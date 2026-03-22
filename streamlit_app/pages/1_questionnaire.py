import sys
from pathlib import Path

import streamlit as st

sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent))

from components.sidebar import render_sidebar
from components.theme import section_header

from app.audit import log_event
from app.database import SessionLocal, init_db
from app.models import Organisation, QuestionnaireProgress
from app.questionnaire import (
    AI_TOOLS_OPTIONS,
    AI_TOOLS_OVERSEAS,
    AUTOMATED_DECISION_TYPES,
    DATA_TYPES_OPTIONS,
    DataRetentionPeriod,
    IndustrySector,
    RevenueRange,
    TrainingFrequency,
)

render_sidebar()


def _build_questionnaire_csv(ans: dict) -> str:
    """Build a CSV string of questionnaire responses for download."""
    import csv
    import io

    _QUESTION_MAP = [
        ("Organisation Profile", None),
        ("business_name", "1. Business name"),
        ("abn", "2. ABN"),
        ("industry", "3. Industry sector"),
        ("employee_count", "4. Number of employees"),
        ("annual_revenue", "5. Annual revenue range"),
        ("AI Tool Usage", None),
        ("ai_tools_in_use", "6. AI tools in use"),
        ("ai_tools_overseas", "7. AI tools processing data overseas"),
        ("shadow_ai_aware", "8. Aware of unapproved AI usage"),
        ("shadow_ai_controls", "9. Shadow AI controls in place"),
        ("Customer-Facing AI & Access Controls", None),
        ("customer_facing_ai", "10. AI generates customer-facing content"),
        ("ai_generated_content_reviewed", "11. AI content reviewed before publication/delivery"),
        ("ai_access_restricted", "12. AI access restricted by role"),
        ("ai_outputs_logged", "13. AI prompts and outputs logged"),
        ("Data & Automated Decisions", None),
        ("data_types_processed", "14. Data types processed with AI"),
        ("trades_in_personal_info", "15. Trades in personal information"),
        ("has_data_retention_policy", "16. Data retention/deletion policy exists"),
        ("consent_mechanism_exists", "17. Consent mechanism for AI data processing"),
        ("automated_decisions", "18. AI used for automated decisions"),
        ("automated_decision_types", "19. Types of automated decisions"),
        ("data_retention_period", "20. Data retention period"),
        ("ai_profiling_or_eligibility", "21. AI used for profiling/eligibility"),
        ("bias_testing_conducted", "22. Bias testing conducted"),
        ("ai_copyright_assessed", "23. Copyright/IP risk assessed"),
        ("ai_in_marketing", "24. AI used in marketing"),
        ("human_review_available", "25. Individuals can request human review of decisions"),
        ("Vendor & Compliance Posture", None),
        ("vendor_dpa_in_place", "26. DPAs with AI vendors"),
        ("pia_conducted", "27. Privacy Impact Assessment conducted"),
        ("has_privacy_policy", "28. Published privacy policy"),
        ("existing_it_policies", "29. Existing IT security policies"),
        ("vendor_ai_clauses_reviewed", "30. Vendor AI clauses reviewed"),
        ("incident_response_tested", "31. Incident response tested"),
        ("vendor_audit_rights", "32. Vendor audit rights in contracts"),
        ("ndb_ai_process", "33. NDB 72-hour notification process"),
        ("ai_incident_register", "34. AI incident register maintained"),
        ("essential_eight_applied", "35. Essential Eight applied to AI"),
        ("Governance", None),
        ("board_ai_awareness", "36. Board/leadership AI briefing"),
        ("training_frequency", "37. Staff training frequency"),
        ("ai_governance_contact", "38. AI governance contact"),
        ("ai_disclosure_to_customers", "39. AI use disclosed to customers"),
        ("ai_supply_chain_assessed", "40. AI supply chain assessed"),
        ("tranche2_aware", "41. POLA Act Tranche 2 awareness"),
        ("data_overseas_mapped", "42. AI data overseas mapped"),
    ]

    _REVENUE_LABELS = {
        "under_3m": "Under $3 million",
        "3m_to_10m": "$3M - $10M",
        "10m_to_50m": "$10M - $50M",
        "over_50m": "Over $50M",
    }

    _RETENTION_LABELS = {
        "30_days": "30 days",
        "90_days": "90 days",
        "1_year": "1 year",
        "3_years": "3 years",
        "no_defined_period": "No defined period",
    }

    buf = io.StringIO()
    writer = csv.writer(buf)
    writer.writerow(["Section / Question", "Response"])

    for key, label in _QUESTION_MAP:
        if label is None:
            writer.writerow([f"--- {key} ---", ""])
            continue
        val = ans.get(key)
        if isinstance(val, bool):
            val = "Yes" if val else "No"
        elif isinstance(val, list):
            val = "; ".join(val) if val else "None"
        elif key == "annual_revenue":
            val = _REVENUE_LABELS.get(val, val)
        elif key == "data_retention_period":
            val = _RETENTION_LABELS.get(val, val)
        elif key == "industry" and val:
            val = val.replace("_", " ").title()
        elif key == "training_frequency" and val:
            val = val.replace("_", " ").title()
        elif val is None:
            val = ""
        writer.writerow([label, val])

    return buf.getvalue()


st.title("Organisation Questionnaire")

# Check if we're in edit mode (editing an existing org)
_editing_org_id = st.session_state.get("q_edit_org_id")
if _editing_org_id:
    st.info(f"Editing questionnaire for organisation ID {_editing_org_id}. Changes will update the existing record.")
else:
    st.write("Answer all questions below to generate tailored AI governance policies aligned with Australian regulations.")

init_db()

# --- Progress Persistence ---
import json
import uuid

if "q_session_key" not in st.session_state:
    st.session_state.q_session_key = str(uuid.uuid4())

def _load_progress():
    """Load saved progress from DB if no session state exists."""
    key = st.session_state.q_session_key
    db = SessionLocal()
    try:
        prog = db.query(QuestionnaireProgress).filter(QuestionnaireProgress.session_key == key).first()
        if prog:
            return prog.step, prog.answers_json or {}
        return 1, {}
    finally:
        db.close()


def _save_progress():
    """Save current progress to DB."""
    key = st.session_state.q_session_key
    db = SessionLocal()
    try:
        prog = db.query(QuestionnaireProgress).filter(QuestionnaireProgress.session_key == key).first()
        if prog:
            prog.step = st.session_state.q_step
            prog.answers_json = st.session_state.q_answers
        else:
            prog = QuestionnaireProgress(
                session_key=key,
                step=st.session_state.q_step,
                answers_json=st.session_state.q_answers,
            )
            db.add(prog)
        db.commit()
    finally:
        db.close()


if "q_step" not in st.session_state:
    saved_step, saved_answers = _load_progress()
    st.session_state.q_step = saved_step
    st.session_state.q_answers = saved_answers
if "q_answers" not in st.session_state:
    st.session_state.q_answers = {}

total_steps = 8
step = st.session_state.q_step
answers = st.session_state.q_answers

_SECTION_NAMES = {
    1: "Organisation Profile",
    2: "AI Tool Usage",
    3: "Customer-Facing AI",
    4: "Data & Automated Decisions",
    5: "Vendor & Compliance",
    6: "Governance",
    7: "Review & Submit",
    8: "Complete",
}
_current_section = _SECTION_NAMES.get(min(step, total_steps), "")
st.progress(
    min(step, total_steps) / total_steps, text=f"Section {min(step, total_steps)} of {total_steps} — {_current_section}"
)


def next_step():
    st.session_state.q_step += 1
    _save_progress()


def prev_step():
    st.session_state.q_step -= 1
    _save_progress()


# === SECTION 1: Organisation Profile ===
if step == 1:
    section_header(1, "Organisation Profile", "Questions 1–5")

    business_name = st.text_input(
        "1. What is your business name? *", value=answers.get("business_name", ""), placeholder="e.g. <Your Organisation Pty Ltd>"
    )

    abn_col1, abn_col2 = st.columns([3, 1])
    with abn_col1:
        abn = st.text_input(
            "2. Australian Business Number (ABN) — optional", value=answers.get("abn", ""), placeholder="12 345 678 901"
        )
    with abn_col2:
        st.markdown("<br>", unsafe_allow_html=True)
        if st.button("Lookup ABN", key="abn_lookup", use_container_width=True):
            abn_digits = abn.replace(" ", "")
            if abn_digits and abn_digits.isdigit() and len(abn_digits) == 11:
                import json
                import urllib.request

                try:
                    url = f"https://abr.business.gov.au/json/AbnDetails.aspx?abn={abn_digits}&callback=cb"
                    req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
                    with urllib.request.urlopen(req, timeout=5) as resp:
                        raw = resp.read().decode("utf-8")
                        json_str = raw[raw.index("(") + 1 : raw.rindex(")")]
                        data = json.loads(json_str)
                        if data.get("Abn"):
                            looked_up_name = data.get("EntityName", "")
                            if looked_up_name:
                                answers["business_name"] = looked_up_name
                                st.success(f"Found: **{looked_up_name}**")
                                st.rerun()
                            else:
                                st.warning("ABN found but no entity name returned.")
                        else:
                            st.warning("ABN not found in the Australian Business Register.")
                except Exception as e:
                    st.warning(f"ABN lookup failed: {e}")
            else:
                st.warning("Enter a valid 11-digit ABN first.")

    industry_options = [e.value for e in IndustrySector]
    current_ind = answers.get("industry", industry_options[0])
    industry = st.selectbox(
        "3. Industry sector *",
        options=industry_options,
        index=industry_options.index(current_ind) if current_ind in industry_options else 0,
        format_func=lambda x: x.replace("_", " ").title(),
    )
    if industry == "technology":
        st.info("Technology companies: Pay special attention to copyright/IP questions — GitHub Copilot and code generation tools create unique IP risks.")
    elif industry in ("healthcare", "finance", "insurance"):
        st.info(f"{industry.title()} sector: Your industry has elevated regulatory requirements. Ensure PIA and DPA questions are answered carefully.")
    employee_count = st.number_input(
        "4. Number of employees *", min_value=1, value=answers.get("employee_count", 10), step=1
    )

    rev_options = [e.value for e in RevenueRange]
    current_rev = answers.get("annual_revenue", rev_options[0])
    annual_revenue = st.selectbox(
        "5. Annual revenue range *",
        options=rev_options,
        index=rev_options.index(current_rev) if current_rev in rev_options else 0,
        format_func=lambda x: {
            "under_3m": "Under $3 million",
            "3m_to_10m": "$3M - $10M",
            "10m_to_50m": "$10M - $50M",
            "over_50m": "Over $50M",
        }.get(x, x),
        help="The Privacy Act currently applies to organisations with >$3M revenue, but this exemption is expected to be removed under Tranche 2.",
    )

    col1, col2 = st.columns(2)
    with col2:
        if st.button("Next →", use_container_width=True, key="s1_next"):
            errors = []
            if not business_name.strip():
                errors.append("Business name is required.")
            if abn.strip():
                digits = abn.replace(" ", "")
                if not digits.isdigit() or len(digits) != 11:
                    errors.append("ABN must be 11 digits.")
            if errors:
                for e in errors:
                    st.error(e)
            if not abn.strip() and annual_revenue in ("10m_to_50m", "over_50m"):
                st.warning("ABN is recommended for organisations with >$10M revenue for ASIC and regulatory compliance.")
            if not errors:
                answers["business_name"] = business_name.strip()
                answers["abn"] = abn.replace(" ", "") if abn.strip() else None
                answers["industry"] = industry
                answers["employee_count"] = employee_count
                answers["annual_revenue"] = annual_revenue
                answers["revenue_exceeds_threshold"] = annual_revenue != "under_3m"
                next_step()
                st.rerun()

# === SECTION 2: AI Tool Usage ===
elif step == 2:
    section_header(2, "AI Tool Usage", "Questions 6–9")

    ai_tools = st.multiselect(
        "6. Which AI tools does your organisation officially use or approve?",
        options=AI_TOOLS_OPTIONS,
        default=answers.get("ai_tools_in_use", []),
        help="Leave empty if your organisation has not yet adopted AI tools. Policies can still be generated proactively.",
    )

    if ai_tools:
        ai_overseas = st.multiselect(
            "7. Which of your AI tools process data in overseas data centres?",
            options=AI_TOOLS_OVERSEAS,
            default=answers.get("ai_tools_overseas", []),
            help="Under APP 8, cross-border disclosure makes your organisation vicariously liable for the overseas provider's data handling.",
        )
    else:
        ai_overseas = answers.get("ai_tools_overseas", [])

    shadow_aware = st.radio(
        "8. Are you aware of employees using AI tools that haven't been approved?",
        options=[True, False],
        index=0 if answers.get("shadow_ai_aware") else 1,
        format_func=lambda x: "Yes" if x else "No",
        horizontal=True,
        help="Research shows 80% of SME employees use unapproved AI tools (Shadow AI).",
    )

    shadow_controls = st.radio(
        "9. Do you have technical or policy controls to detect/prevent unapproved AI usage?",
        options=[True, False],
        index=0 if answers.get("shadow_ai_controls") else 1,
        format_func=lambda x: "Yes" if x else "No",
        horizontal=True,
    )

    col1, col2 = st.columns(2)
    with col1:
        if st.button("← Back", use_container_width=True, key="s2_back"):
            prev_step()
            st.rerun()
    with col2:
        if st.button("Next →", use_container_width=True, key="s2_next"):
            answers["ai_tools_in_use"] = ai_tools
            answers["ai_tools_overseas"] = ai_overseas
            answers["shadow_ai_aware"] = shadow_aware
            answers["shadow_ai_controls"] = shadow_controls
            next_step()
            st.rerun()

# === SECTION 3: Customer-Facing AI & Access Controls ===
elif step == 3:
    section_header(3, "Customer-Facing AI & Access Controls", "Questions 10–13")

    customer_ai = st.radio(
        "10. Does your organisation use AI to generate customer-facing content?",
        options=[True, False],
        index=0 if answers.get("customer_facing_ai") else 1,
        format_func=lambda x: "Yes" if x else "No",
        horizontal=True,
        help="This includes marketing copy, product descriptions, chatbot responses, recommendations. Triggers ACL obligations.",
    )

    reviewed = st.radio(
        "11. Is all AI-generated customer-facing content reviewed by a human before publication or delivery?",
        options=[True, False],
        index=0 if answers.get("ai_generated_content_reviewed") else 1,
        format_func=lambda x: "Yes" if x else "No",
        horizontal=True,
        help="This is about content quality review BEFORE customers see it (marketing, chatbot responses, recommendations). Triggers ACL strict liability if 'No'.",
    )

    ai_restricted = st.radio(
        "12. Is access to AI tools restricted by role (not all employees have access)?",
        options=[True, False],
        index=0 if answers.get("ai_access_restricted") else 1,
        format_func=lambda x: "Yes" if x else "No",
        horizontal=True,
        help="Role-based access reduces risk of sensitive data exposure through AI tools.",
    )

    ai_logged = st.radio(
        "13. Are AI prompts and outputs logged or recorded for audit purposes?",
        options=[True, False],
        index=0 if answers.get("ai_outputs_logged") else 1,
        format_func=lambda x: "Yes" if x else "No",
        horizontal=True,
        help="Logging AI interactions supports incident investigation, compliance evidence, and quality assurance.",
    )

    col1, col2 = st.columns(2)
    with col1:
        if st.button("← Back", use_container_width=True, key="s3_back"):
            prev_step()
            st.rerun()
    with col2:
        if st.button("Next →", use_container_width=True, key="s3_next"):
            answers["customer_facing_ai"] = customer_ai
            answers["ai_generated_content_reviewed"] = reviewed
            answers["ai_access_restricted"] = ai_restricted
            answers["ai_outputs_logged"] = ai_logged
            next_step()
            st.rerun()

# === SECTION 4: Data & Automated Decisions ===
elif step == 4:
    section_header(4, "Data & Automated Decisions", "Questions 14–25")

    data_types = st.multiselect(
        "14. What types of data does your organisation process using AI tools? *",
        options=DATA_TYPES_OPTIONS,
        default=answers.get("data_types_processed", []),
    )

    trades_pi = st.radio(
        "15. Does your business 'trade in' personal information?",
        options=[True, False],
        index=0 if answers.get("trades_in_personal_info") else 1,
        format_func=lambda x: "Yes" if x else "No",
        horizontal=True,
        help="E.g., sell customer lists, data brokering, lead generation. Covered by Privacy Act regardless of revenue.",
    )

    data_retention = st.radio(
        "16. Do you have a data retention and deletion policy for AI-processed data and outputs?",
        options=[True, False],
        index=0 if answers.get("has_data_retention_policy") else 1,
        format_func=lambda x: "Yes" if x else "No",
        horizontal=True,
        help="APP 11 requires destruction or de-identification of personal information no longer needed.",
    )

    consent = st.radio(
        "17. Do you have a mechanism to obtain consent before processing personal information through AI tools?",
        options=[True, False],
        index=0 if answers.get("consent_mechanism_exists") else 1,
        format_func=lambda x: "Yes" if x else "No",
        horizontal=True,
        help="APP 3 and APP 6 require consent for collection and use of personal information.",
    )

    auto_decisions = st.radio(
        "18. Does your organisation use AI for automated decisions affecting individuals?",
        options=[True, False],
        index=0 if answers.get("automated_decisions") else 1,
        format_func=lambda x: "Yes" if x else "No",
        horizontal=True,
        help="Under the POLA Act 2024, you must disclose automated decisions in your privacy policy by December 2026.",
    )

    if auto_decisions:
        auto_types = st.multiselect(
            "19. What types of automated decisions?",
            options=AUTOMATED_DECISION_TYPES,
            default=answers.get("automated_decision_types", []),
        )
    else:
        auto_types = answers.get("automated_decision_types", [])

    retention_options = [e.value for e in DataRetentionPeriod]
    current_retention = answers.get("data_retention_period", "no_defined_period")
    data_retention_period = st.selectbox(
        "20. What is the defined data retention period for AI-processed personal information?",
        options=retention_options,
        index=retention_options.index(current_retention)
        if current_retention in retention_options
        else len(retention_options) - 1,
        format_func=lambda x: {
            "30_days": "30 days",
            "90_days": "90 days",
            "1_year": "1 year",
            "3_years": "3 years",
            "no_defined_period": "No defined period",
        }.get(x, x),
        help="APP 11 requires destruction or de-identification of personal information no longer needed. Define a retention ceiling.",
    )

    profiling = st.radio(
        "21. Do you use AI for profiling individuals or making eligibility/access decisions?",
        options=[True, False],
        index=0 if answers.get("ai_profiling_or_eligibility") else 1,
        format_func=lambda x: "Yes" if x else "No",
        horizontal=True,
        help="APPs 3.6 and 6.1 impose strict requirements on using personal information for profiling and eligibility decisions.",
    )

    bias_tested = st.radio(
        "22. Have you assessed AI outputs for bias against protected attributes (age, gender, race, disability)?",
        options=[True, False],
        index=0 if answers.get("bias_testing_conducted") else 1,
        format_func=lambda x: "Yes" if x else "No",
        horizontal=True,
        help="AI Ethics Principle 2 (Fairness) and anti-discrimination laws require testing for bias in AI-assisted decisions.",
    )

    copyright_assessed = st.radio(
        "23. Have you assessed copyright ownership of AI-generated content your organisation uses?",
        options=[True, False],
        index=0 if answers.get("ai_copyright_assessed") else 1,
        format_func=lambda x: "Yes" if x else "No",
        horizontal=True,
        help="Under the Copyright Act 1968, AI-generated works may not have copyright protection.",
    )

    in_marketing = st.radio(
        "24. Do you use AI-generated content in marketing, advertising, or product descriptions?",
        options=[True, False],
        index=0 if answers.get("ai_in_marketing") else 1,
        format_func=lambda x: "Yes" if x else "No",
        horizontal=True,
        help="ACL s18 imposes strict liability for misleading or deceptive conduct — AI-generated marketing claims must be accurate.",
    )

    human_review = st.radio(
        "25. Can individuals request a human review of automated decisions that affect them?",
        options=[True, False],
        index=0 if answers.get("human_review_available") else 1,
        format_func=lambda x: "Yes" if x else "No",
        horizontal=True,
        help="AI Ethics Principle 7 (Contestability) requires that individuals can challenge AI decisions that affect them.",
    )

    col1, col2 = st.columns(2)
    with col1:
        if st.button("← Back", use_container_width=True, key="s4_back"):
            prev_step()
            st.rerun()
    with col2:
        if st.button("Next →", use_container_width=True, key="s4_next"):
            if not data_types:
                st.error("Select at least one data type.")
            else:
                answers["data_types_processed"] = data_types
                answers["trades_in_personal_info"] = trades_pi
                answers["has_data_retention_policy"] = data_retention
                answers["data_retention_period"] = data_retention_period
                answers["consent_mechanism_exists"] = consent
                answers["automated_decisions"] = auto_decisions
                answers["automated_decision_types"] = auto_types
                answers["ai_profiling_or_eligibility"] = profiling
                answers["bias_testing_conducted"] = bias_tested
                answers["ai_copyright_assessed"] = copyright_assessed
                answers["ai_in_marketing"] = in_marketing
                answers["human_review_available"] = human_review
                next_step()
                st.rerun()

# === SECTION 5: Vendor & Compliance Posture ===
elif step == 5:
    section_header(5, "Vendor & Compliance Posture", "Questions 26–34")

    vendor_dpa = st.radio(
        "26. Do you have Data Processing Agreements (DPAs) with your AI tool vendors?",
        options=[True, False],
        index=0 if answers.get("vendor_dpa_in_place") else 1,
        format_func=lambda x: "Yes" if x else "No",
        horizontal=True,
        help="DPAs establish contractual obligations for vendor data handling — critical for APP 8.",
    )

    pia = st.radio(
        "27. Have you conducted a Privacy Impact Assessment (PIA) for any AI tool?",
        options=[True, False],
        index=0 if answers.get("pia_conducted") else 1,
        format_func=lambda x: "Yes" if x else "No",
        horizontal=True,
        help="The OAIC recommends PIAs before deploying AI systems that process personal information.",
    )

    has_privacy = st.radio(
        "28. Does your organisation have a published privacy policy?",
        options=[True, False],
        index=0 if answers.get("has_privacy_policy") else 1,
        format_func=lambda x: "Yes" if x else "No",
        horizontal=True,
        help="APP 1 requires organisations to have a clearly expressed privacy policy. The POLA Act requires updating it for automated decisions.",
    )

    it_policies = st.radio(
        "29. Does your organisation have existing IT security policies?",
        options=[True, False],
        index=0 if answers.get("existing_it_policies") else 1,
        format_func=lambda x: "Yes" if x else "No",
        horizontal=True,
    )

    vendor_ai_clauses = st.radio(
        "30. Have vendor contracts been reviewed for AI-specific clauses (model training opt-out, sub-processor lists)?",
        options=[True, False],
        index=0 if answers.get("vendor_ai_clauses_reviewed") else 1,
        format_func=lambda x: "Yes" if x else "No",
        horizontal=True,
        help="AI vendors may train on your data unless you contractually opt out. Review contracts for model-training, sub-processor, and IP clauses.",
    )

    ir_tested = st.radio(
        "31. Has your incident response been tested (tabletop exercise) in the past 12 months?",
        options=[True, False],
        index=0 if answers.get("incident_response_tested") else 1,
        format_func=lambda x: "Yes" if x else "No",
        horizontal=True,
    )

    vendor_audit = st.radio(
        "32. Do your contracts with AI vendors include audit or inspection rights?",
        options=[True, False],
        index=0 if answers.get("vendor_audit_rights") else 1,
        format_func=lambda x: "Yes" if x else "No",
        horizontal=True,
        help="Audit rights allow your organisation to verify vendor compliance with contractual and regulatory obligations.",
    )

    ndb_process = st.radio(
        "33. Do you have a process for notifying the OAIC within 72 hours if an AI system is involved in a data breach?",
        options=[True, False],
        index=0 if answers.get("ndb_ai_process") else 1,
        format_func=lambda x: "Yes" if x else "No",
        horizontal=True,
        help="The NDB scheme requires notification to the OAIC within 30 days, but best practice is 72 hours.",
    )

    ai_incident_reg = st.radio(
        "34. Do you maintain a dedicated AI incident register (separate from general IT incidents)?",
        options=[True, False],
        index=0 if answers.get("ai_incident_register") else 1,
        format_func=lambda x: "Yes" if x else "No",
        horizontal=True,
        help="AI-specific incidents (bias, hallucination, data leakage) require dedicated tracking.",
    )

    e8_applied = st.radio(
        "35. Has your organisation applied the ACSC Essential Eight security controls to AI systems?",
        options=[True, False],
        index=0 if answers.get("essential_eight_applied") else 1,
        format_func=lambda x: "Yes" if x else "No",
        horizontal=True,
        help="The ACSC Essential Eight (application control, patching, MFA, etc.) should extend to AI tools.",
    )

    col1, col2 = st.columns(2)
    with col1:
        if st.button("← Back", use_container_width=True, key="s5_back"):
            prev_step()
            st.rerun()
    with col2:
        if st.button("Next →", use_container_width=True, key="s5_next"):
            answers["vendor_dpa_in_place"] = vendor_dpa
            answers["pia_conducted"] = pia
            answers["has_privacy_policy"] = has_privacy
            answers["existing_it_policies"] = it_policies
            answers["incident_response_tested"] = ir_tested
            answers["vendor_ai_clauses_reviewed"] = vendor_ai_clauses
            answers["vendor_audit_rights"] = vendor_audit
            answers["ndb_ai_process"] = ndb_process
            answers["ai_incident_register"] = ai_incident_reg
            answers["essential_eight_applied"] = e8_applied
            next_step()
            st.rerun()

# === SECTION 6: Governance ===
elif step == 6:
    section_header(6, "Governance", "Questions 36–42")

    board_aware = st.radio(
        "36. Has your board or senior leadership been briefed on AI risks and governance obligations?",
        options=[True, False],
        index=0 if answers.get("board_ai_awareness") else 1,
        format_func=lambda x: "Yes" if x else "No",
        horizontal=True,
        help="Directors have a duty of care under the Corporations Act to understand material risks including AI.",
    )

    freq_options = [e.value for e in TrainingFrequency]
    current_freq = answers.get("training_frequency", "annually")
    training = st.selectbox(
        "37. How frequently do staff receive training on data privacy and AI usage?",
        options=freq_options,
        index=freq_options.index(current_freq) if current_freq in freq_options else 3,
        format_func=lambda x: x.replace("_", " ").title(),
        help="The OAIC recommends bi-annual staff training on AI and privacy.",
    )

    governance = st.text_input(
        "38. Named AI governance contact (optional)",
        value=answers.get("ai_governance_contact", ""),
        placeholder="Jane Smith, Head of IT",
        help="AI Ethics Principle 8 (Accountability) requires identifiable individuals responsible for AI outcomes.",
    )

    ai_disclose = st.radio(
        "39. Do customers know when they are interacting with AI?",
        options=[True, False],
        index=0 if answers.get("ai_disclosure_to_customers") else 1,
        format_func=lambda x: "Yes" if x else "No",
        horizontal=True,
        help="POLA Act s15 and AI Ethics Principle 4 (Transparency) require disclosure when AI is used in customer interactions.",
    )

    supply_chain = st.radio(
        "40. Have you assessed the AI supply chain (sub-processors, model providers, data sources)?",
        options=[True, False],
        index=0 if answers.get("ai_supply_chain_assessed") else 1,
        format_func=lambda x: "Yes" if x else "No",
        horizontal=True,
        help="Understanding your AI supply chain is critical for APP 8 compliance and managing third-party risk.",
    )

    tranche2 = st.radio(
        "41. Are you aware of POLA Act Tranche 2 requirements for high-risk AI systems?",
        options=[True, False],
        index=0 if answers.get("tranche2_aware") else 1,
        format_func=lambda x: "Yes" if x else "No",
        horizontal=True,
        help="Tranche 2 may introduce mandatory conformity assessments, high-risk AI registers, and additional obligations.",
    )

    data_mapped = st.radio(
        "42. Have you mapped which AI tools store or process data outside Australia?",
        options=[True, False],
        index=0 if answers.get("data_overseas_mapped") else 1,
        format_func=lambda x: "Yes" if x else "No",
        horizontal=True,
        help="APP 8 requires you to know where personal information is being disclosed overseas.",
    )

    col1, col2 = st.columns(2)
    with col1:
        if st.button("← Back", use_container_width=True, key="s6_back"):
            prev_step()
            st.rerun()
    with col2:
        if st.button("Next → Review", use_container_width=True, key="s6_next"):
            answers["board_ai_awareness"] = board_aware
            answers["training_frequency"] = training
            answers["ai_governance_contact"] = governance.strip() or None
            answers["ai_disclosure_to_customers"] = ai_disclose
            answers["ai_supply_chain_assessed"] = supply_chain
            answers["tranche2_aware"] = tranche2
            answers["data_overseas_mapped"] = data_mapped
            next_step()
            st.rerun()

# === SECTION 7: Review & Submit ===
elif step == 7:
    section_header(7, "Review & Submit", "Verify your answers before submitting")

    def _yn(val):
        return "Yes" if val else "No"

    rev_labels = {"under_3m": "Under $3M", "3m_to_10m": "$3M-$10M", "10m_to_50m": "$10M-$50M", "over_50m": "Over $50M"}

    st.markdown(
        """<div class="section-card"><div class="section-card-header">Organisation Profile</div></div>""",
        unsafe_allow_html=True,
    )
    st.write(f"Business Name: **{answers.get('business_name')}**")
    st.write(f"Industry: **{answers.get('industry', '').replace('_', ' ').title()}**")
    st.write(f"Employees: **{answers.get('employee_count')}**")
    st.write(f"Revenue: **{rev_labels.get(answers.get('annual_revenue', ''), 'N/A')}**")

    st.markdown(
        """<div class="section-card"><div class="section-card-header">AI Tool Usage</div></div>""",
        unsafe_allow_html=True,
    )
    tools = answers.get("ai_tools_in_use", [])
    st.write(f"AI Tools: **{', '.join(tools) if tools else 'None (pre-adoption)'}**")
    st.write(f"Overseas Tools: **{', '.join(answers.get('ai_tools_overseas', [])) or 'None'}**")
    st.write(
        f"Shadow AI Aware: **{_yn(answers.get('shadow_ai_aware'))}** | Controls: **{_yn(answers.get('shadow_ai_controls'))}**"
    )
    st.write(
        f"AI Access Restricted: **{_yn(answers.get('ai_access_restricted'))}** | Outputs Logged: **{_yn(answers.get('ai_outputs_logged'))}**"
    )

    st.markdown(
        """<div class="section-card"><div class="section-card-header">Customer-Facing AI</div></div>""",
        unsafe_allow_html=True,
    )
    st.write(
        f"Customer-Facing AI: **{_yn(answers.get('customer_facing_ai'))}** | Content Pre-Review: **{_yn(answers.get('ai_generated_content_reviewed'))}**"
    )

    st.markdown(
        """<div class="section-card"><div class="section-card-header">Data & Decisions</div></div>""",
        unsafe_allow_html=True,
    )
    st.write(f"Data Types: **{', '.join(answers.get('data_types_processed', []))}**")
    st.write(
        f"Trades in PI: **{_yn(answers.get('trades_in_personal_info'))}** | Data Retention Policy: **{_yn(answers.get('has_data_retention_policy'))}**"
    )
    st.write(
        f"Data Retention Period: **{answers.get('data_retention_period', 'no_defined_period').replace('_', ' ').title()}**"
    )
    st.write(f"Consent Mechanism: **{_yn(answers.get('consent_mechanism_exists'))}**")
    st.write(f"Automated Decisions: **{_yn(answers.get('automated_decisions'))}**")
    if answers.get("automated_decisions"):
        st.write(f"Decision Types: **{', '.join(answers.get('automated_decision_types', []))}**")
    st.write(
        f"AI Profiling/Eligibility: **{_yn(answers.get('ai_profiling_or_eligibility'))}** | Bias Testing: **{_yn(answers.get('bias_testing_conducted'))}**"
    )
    st.write(
        f"Copyright Assessed: **{_yn(answers.get('ai_copyright_assessed'))}** | AI in Marketing: **{_yn(answers.get('ai_in_marketing'))}**"
    )
    st.write(f"Contestable Decisions (Human Review): **{_yn(answers.get('human_review_available'))}**")

    st.markdown(
        """<div class="section-card"><div class="section-card-header">Vendor & Compliance Posture</div></div>""",
        unsafe_allow_html=True,
    )
    st.write(f"DPAs: **{_yn(answers.get('vendor_dpa_in_place'))}** | PIA: **{_yn(answers.get('pia_conducted'))}**")
    st.write(
        f"Privacy Policy: **{_yn(answers.get('has_privacy_policy'))}** | IT Policies: **{_yn(answers.get('existing_it_policies'))}**"
    )
    st.write(f"Incident Response Tested: **{_yn(answers.get('incident_response_tested'))}**")
    st.write(f"Vendor AI Clauses Reviewed: **{_yn(answers.get('vendor_ai_clauses_reviewed'))}**")
    st.write(
        f"Vendor Audit Rights: **{_yn(answers.get('vendor_audit_rights'))}** | NDB Process: **{_yn(answers.get('ndb_ai_process'))}**"
    )
    st.write(
        f"AI Incident Register: **{_yn(answers.get('ai_incident_register'))}** | Essential Eight: **{_yn(answers.get('essential_eight_applied'))}**"
    )

    st.markdown(
        """<div class="section-card"><div class="section-card-header">Governance</div></div>""", unsafe_allow_html=True
    )
    st.write(f"Board AI Briefing: **{_yn(answers.get('board_ai_awareness'))}**")
    st.write(f"Training: **{answers.get('training_frequency', 'N/A').replace('_', ' ').title()}**")
    st.write(f"Governance Contact: **{answers.get('ai_governance_contact') or 'Not specified'}**")
    st.write(
        f"AI Disclosure to Customers: **{_yn(answers.get('ai_disclosure_to_customers'))}** | Supply Chain Assessed: **{_yn(answers.get('ai_supply_chain_assessed'))}**"
    )
    st.write(
        f"Tranche 2 Aware: **{_yn(answers.get('tranche2_aware'))}** | Data Overseas Mapped: **{_yn(answers.get('data_overseas_mapped'))}**"
    )

    _csv_data = _build_questionnaire_csv(answers)
    _safe_name = "".join(c if c.isalnum() or c in "-_ " else "" for c in answers.get("business_name", "questionnaire"))[:80]
    st.download_button(
        label="Download Responses as CSV",
        data=_csv_data,
        file_name=f"questionnaire_{_safe_name}.csv",
        mime="text/csv",
        key="dl_csv_review",
        use_container_width=True,
    )

    col1, col2 = st.columns(2)
    with col1:
        if st.button("← Edit Answers", use_container_width=True, key="s7_back"):
            prev_step()
            st.rerun()
    with col2:
        submit_label = "Update Questionnaire" if _editing_org_id else "Submit Questionnaire"
        if st.button(submit_label, type="primary", use_container_width=True, key="s7_submit"):
            db = SessionLocal()
            try:
                _field_map = {
                    "business_name": answers["business_name"],
                    "abn": answers.get("abn"),
                    "industry": answers["industry"],
                    "employee_count": answers["employee_count"],
                    "annual_revenue": answers.get("annual_revenue", "under_3m"),
                    "revenue_exceeds_threshold": answers.get("revenue_exceeds_threshold", False),
                    "ai_tools_in_use": answers.get("ai_tools_in_use", []),
                    "ai_tools_overseas": answers.get("ai_tools_overseas", []),
                    "shadow_ai_aware": answers.get("shadow_ai_aware", False),
                    "shadow_ai_controls": answers.get("shadow_ai_controls", False),
                    "customer_facing_ai": answers.get("customer_facing_ai", False),
                    "ai_generated_content_reviewed": answers.get("ai_generated_content_reviewed", False),
                    "ai_access_restricted": answers.get("ai_access_restricted", False),
                    "ai_outputs_logged": answers.get("ai_outputs_logged", False),
                    "automated_decisions": answers.get("automated_decisions", False),
                    "automated_decision_types": answers.get("automated_decision_types", []),
                    "data_types_processed": answers["data_types_processed"],
                    "trades_in_personal_info": answers.get("trades_in_personal_info", False),
                    "has_data_retention_policy": answers.get("has_data_retention_policy", False),
                    "data_retention_period": answers.get("data_retention_period", "no_defined_period"),
                    "consent_mechanism_exists": answers.get("consent_mechanism_exists", False),
                    "vendor_dpa_in_place": answers.get("vendor_dpa_in_place", False),
                    "pia_conducted": answers.get("pia_conducted", False),
                    "has_privacy_policy": answers.get("has_privacy_policy", False),
                    "vendor_ai_clauses_reviewed": answers.get("vendor_ai_clauses_reviewed", False),
                    "existing_it_policies": answers.get("existing_it_policies", False),
                    "incident_response_tested": answers.get("incident_response_tested", False),
                    "board_ai_awareness": answers.get("board_ai_awareness", False),
                    "training_frequency": answers.get("training_frequency", "annually"),
                    "ai_governance_contact": answers.get("ai_governance_contact"),
                    "ai_profiling_or_eligibility": answers.get("ai_profiling_or_eligibility", False),
                    "bias_testing_conducted": answers.get("bias_testing_conducted", False),
                    "ai_copyright_assessed": answers.get("ai_copyright_assessed", False),
                    "ai_in_marketing": answers.get("ai_in_marketing", False),
                    "human_review_available": answers.get("human_review_available", False),
                    "vendor_audit_rights": answers.get("vendor_audit_rights", False),
                    "ndb_ai_process": answers.get("ndb_ai_process", False),
                    "ai_incident_register": answers.get("ai_incident_register", False),
                    "essential_eight_applied": answers.get("essential_eight_applied", False),
                    "ai_disclosure_to_customers": answers.get("ai_disclosure_to_customers", False),
                    "ai_supply_chain_assessed": answers.get("ai_supply_chain_assessed", False),
                    "tranche2_aware": answers.get("tranche2_aware", False),
                    "data_overseas_mapped": answers.get("data_overseas_mapped", False),
                }

                if _editing_org_id:
                    # Update existing organisation
                    org = db.query(Organisation).filter(Organisation.id == _editing_org_id).first()
                    if not org:
                        st.error("Organisation not found.")
                        db.close()
                        st.stop()
                    for field, value in _field_map.items():
                        setattr(org, field, value)
                    db.commit()
                    db.refresh(org)

                    log_event(
                        db,
                        event_type="questionnaire_updated",
                        org_id=org.id,
                        metadata={"industry": org.industry, "employee_count": org.employee_count},
                    )

                    # Clear edit mode, snapshot cache, and compliance cache so scores recalculate
                    st.session_state.pop("q_edit_org_id", None)
                    for key in list(st.session_state.keys()):
                        if key.startswith("snapshot_saved_"):
                            del st.session_state[key]
                    st.cache_data.clear()

                    st.session_state.org_id = org.id
                    st.session_state.business_name = org.business_name
                    st.session_state.q_step = total_steps + 1
                    # Track org in current session for data isolation
                    st.session_state.setdefault("session_org_ids", set()).add(org.id)

                    st.success(f"Questionnaire updated for {org.business_name}!")
                else:
                    # Create new organisation
                    org = Organisation(**_field_map)
                    db.add(org)
                    db.commit()
                    db.refresh(org)

                    log_event(
                        db,
                        event_type="questionnaire_submitted",
                        org_id=org.id,
                        metadata={"industry": org.industry, "employee_count": org.employee_count},
                    )

                    st.session_state.org_id = org.id
                    st.session_state.business_name = org.business_name
                    st.session_state.q_step = total_steps + 1
                    # Track org in current session for data isolation
                    st.session_state.setdefault("session_org_ids", set()).add(org.id)

                    st.success(f"Questionnaire submitted! Organisation ID: {org.id}")
                    st.info("Navigate to the **Generate** page to create your policy documents.")
            finally:
                db.close()

elif step > total_steps:
    st.success(f"Questionnaire complete for **{st.session_state.get('business_name', '')}**")
    st.info("Go to the **Generate** page to create your policy documents, then check your **Compliance Scorecard**.")

    if answers:
        _csv_done = _build_questionnaire_csv(answers)
        _safe_done = "".join(
            c if c.isalnum() or c in "-_ " else "" for c in st.session_state.get("business_name", "questionnaire")
        )[:80]
        st.download_button(
            label="Download Submitted Responses as CSV",
            data=_csv_done,
            file_name=f"questionnaire_{_safe_done}.csv",
            mime="text/csv",
            key="dl_csv_done",
            use_container_width=True,
        )

    if st.button("Start Over"):
        st.session_state.q_step = 1
        st.session_state.q_answers = {}
        st.session_state.pop("q_edit_org_id", None)
        for key in ("org_id", "business_name"):
            st.session_state.pop(key, None)
        st.rerun()
