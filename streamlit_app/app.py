import sys
from pathlib import Path

import streamlit as st

st.set_page_config(
    page_title="AI Compliance Policy Generator",
    page_icon="shield",
    layout="wide",
    initial_sidebar_state="expanded",
)

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from components.sidebar import render_sidebar

from app.database import SessionLocal, init_db
from app.models import Organisation, PolicyDocument, org_to_dict

init_db()

try:
    from app.rag_service import rag_service

    rag_service.initialize()
except Exception:
    pass  # RAG is optional

render_sidebar()

# --- Hero Section ---
st.markdown(
    """
<div style="background:linear-gradient(135deg, #1a3c6e 0%, #2d5fa1 60%, #3b82f6 100%);
            padding:40px 36px 32px 36px; border-radius:16px; margin-bottom:24px;">
    <div style="font-size:2.4rem; font-weight:800; color:#ffffff; letter-spacing:-0.03em;">
        AI Compliance Policy Generator
    </div>
    <div style="font-size:1.1rem; color:#c7d8f0; margin-top:6px;">
        Generate regulation-aligned AI governance policies, compliance scorecards, and penalty exposure reports for Australian organisations
    </div>
</div>
""",
    unsafe_allow_html=True,
)

# --- Clear stale session state from previous visitors ---
_session_org_ids = st.session_state.get("session_org_ids", set())
if st.session_state.get("org_id") and st.session_state.get("org_id") not in _session_org_ids:
    for _stale_key in ["org_id", "business_name", "q_step", "q_answers", "q_session_key", "q_edit_org_id", "preselect_templates", "logo_path"]:
        st.session_state.pop(_stale_key, None)
    for _key in list(st.session_state.keys()):
        if _key.startswith(("snapshot_saved_", "_compliance_report", "_remediation", "_ev_saved_", "_logo_saved_")):
            del st.session_state[_key]

# --- Check if org exists and belongs to this session ---
has_org = (
    "org_id" in st.session_state
    and st.session_state.get("org_id")
    and st.session_state.get("org_id") in _session_org_ids
)

if has_org:
    org_id = st.session_state.org_id
    db = SessionLocal()
    try:
        org = db.query(Organisation).filter(Organisation.id == org_id).first()

        if org:
            policies = db.query(PolicyDocument).filter(PolicyDocument.org_id == org_id).all()
            policy_types = {p.template_type for p in policies}
            policy_count = len(policies)

            # Get compliance score (cached to avoid recalculating on every page load)
            from app.compliance_checker import calculate_compliance_score

            @st.cache_data(ttl=300, show_spinner=False)
            def _cached_compliance(oid: int, _policy_types_hash: str):
                _db = SessionLocal()
                try:
                    _org = _db.query(Organisation).filter(Organisation.id == oid).first()
                    if not _org:
                        return None
                    _org_data = org_to_dict(_org)
                    _ptypes = set(_policy_types_hash.split(",")) if _policy_types_hash else set()
                    return calculate_compliance_score(_org_data, _ptypes)
                finally:
                    _db.close()

            _ptypes_hash = ",".join(sorted(policy_types))
            result = _cached_compliance(org_id, _ptypes_hash)
            if result is None:
                st.error("Organisation not found.")
                st.stop()
            score = result["score_percentage"]
            risk = result["risk_rating"]
            penalty_total = result["penalty_exposure"]["total_maximum_exposure"]

            # --- Dashboard Metrics ---
            st.markdown(f"### Dashboard: {org.business_name}")

            col1, col2, col3, col4 = st.columns(4)
            with col1:
                st.metric("Compliance Score", f"{score}%")
            with col2:
                st.metric("Risk Rating", risk)
            with col3:
                st.metric("Policies Generated", policy_count)
            with col4:
                st.metric("Penalty Exposure", f"${penalty_total:,.0f}")

            st.markdown("")

            # --- Score Gauge ---
            import plotly.graph_objects as go

            fig = go.Figure(
                go.Indicator(
                    mode="gauge+number",
                    value=score,
                    number={"suffix": "%", "font": {"size": 48, "color": "#1a3c6e"}},
                    gauge={
                        "axis": {"range": [0, 100], "tickwidth": 1, "tickcolor": "#e2e8f0"},
                        "bar": {"color": "#1a3c6e", "thickness": 0.3},
                        "bgcolor": "#f1f5f9",
                        "steps": [
                            {"range": [0, 25], "color": "#fee2e2"},
                            {"range": [25, 50], "color": "#fef3c7"},
                            {"range": [50, 75], "color": "#dbeafe"},
                            {"range": [75, 100], "color": "#dcfce7"},
                        ],
                        "threshold": {
                            "line": {"color": "#dc2626", "width": 3},
                            "thickness": 0.8,
                            "value": score,
                        },
                    },
                    title={"text": "Overall Compliance", "font": {"size": 16, "color": "#64748b"}},
                )
            )
            fig.update_layout(
                height=280,
                margin=dict(l=30, r=30, t=60, b=10),
                paper_bgcolor="rgba(0,0,0,0)",
                font={"family": "Inter, sans-serif"},
            )

            col_gauge, col_status = st.columns([1, 1])
            with col_gauge:
                st.plotly_chart(fig, use_container_width=True)

            with col_status:
                st.markdown("#### Quick Status")

                core_policies = ["ai_acceptable_use", "data_classification", "incident_response"]
                policy_labels = {
                    "ai_acceptable_use": "AI Acceptable Use Policy",
                    "data_classification": "Data Classification Policy",
                    "incident_response": "Incident Response Plan",
                }
                for p in core_policies:
                    if p in policy_types:
                        st.markdown(f"[Done] **{policy_labels[p]}**")
                    else:
                        st.markdown(f"[ ] **{policy_labels[p]}** — *not generated*")

                st.markdown("")
                critical_count = len(result["critical_gaps"])
                high_count = len(result["high_gaps"])
                if critical_count > 0:
                    st.error(f"{critical_count} critical gap(s) need immediate attention")
                if high_count > 0:
                    st.warning(f"{high_count} high-priority gap(s) to address")
                if critical_count == 0 and high_count == 0:
                    st.success("No critical or high-priority gaps!")

                # POLA Act countdown
                from datetime import date

                pola_deadline = date(2026, 12, 10)
                days_left = (pola_deadline - date.today()).days
                if days_left > 0:
                    st.markdown(f"**POLA Act Deadline:** {days_left} days remaining")
                else:
                    st.error("POLA Act deadline has passed!")

            # --- Quick Actions ---
            st.markdown("### Quick Actions")
            qa1, qa2, qa3, qa4 = st.columns(4)
            with qa1:
                st.markdown(
                    """
                <div class="quick-action-card">
                    <div class="qa-icon"><span style="background:#eff6ff;color:#1a3c6e;width:44px;height:44px;border-radius:12px;display:inline-flex;align-items:center;justify-content:center;font-size:1.3rem;font-weight:800;">P</span></div>
                    <div class="qa-label">Generate Policies</div>
                    <div class="qa-desc">Create tailored AI governance documents</div>
                </div>
                """,
                    unsafe_allow_html=True,
                )
                st.page_link("pages/2_generate.py", label="Go to Generate", use_container_width=True)
            with qa2:
                st.markdown(
                    """
                <div class="quick-action-card">
                    <div class="qa-icon"><span style="background:#f0fdf4;color:#16a34a;width:44px;height:44px;border-radius:12px;display:inline-flex;align-items:center;justify-content:center;font-size:1.3rem;font-weight:800;">S</span></div>
                    <div class="qa-label">Compliance Scorecard</div>
                    <div class="qa-desc">View gaps, scores & penalty exposure</div>
                </div>
                """,
                    unsafe_allow_html=True,
                )
                st.page_link("pages/4_compliance.py", label="Go to Scorecard", use_container_width=True)
            with qa3:
                st.markdown(
                    """
                <div class="quick-action-card">
                    <div class="qa-icon"><span style="background:#faf5ff;color:#7c3aed;width:44px;height:44px;border-radius:12px;display:inline-flex;align-items:center;justify-content:center;font-size:1.3rem;font-weight:800;">D</span></div>
                    <div class="qa-label">Download Policies</div>
                    <div class="qa-desc">Access generated policy documents</div>
                </div>
                """,
                    unsafe_allow_html=True,
                )
                st.page_link("pages/3_policies.py", label="Go to Policies", use_container_width=True)
            with qa4:
                st.markdown(
                    """
                <div class="quick-action-card">
                    <div class="qa-icon"><span style="background:#fff7ed;color:#ea580c;width:44px;height:44px;border-radius:12px;display:inline-flex;align-items:center;justify-content:center;font-size:1.3rem;font-weight:800;">Q</span></div>
                    <div class="qa-label">Edit Questionnaire</div>
                    <div class="qa-desc">Update your organisation's answers</div>
                </div>
                """,
                    unsafe_allow_html=True,
                )
                if st.button("Go →", use_container_width=True, key="edit_questionnaire_btn"):
                    # Load org data into questionnaire answers for editing
                    org_dict = org_to_dict(org)
                    st.session_state.q_answers = {
                        "business_name": org_dict["business_name"],
                        "abn": org_dict["abn"],
                        "industry": org_dict["industry"],
                        "employee_count": org_dict["employee_count"],
                        "annual_revenue": org_dict["annual_revenue"],
                        "revenue_exceeds_threshold": org_dict["revenue_exceeds_threshold"],
                        "ai_tools_in_use": org_dict["ai_tools_in_use"],
                        "ai_tools_overseas": org_dict["ai_tools_overseas"],
                        "shadow_ai_aware": org_dict["shadow_ai_aware"],
                        "shadow_ai_controls": org_dict["shadow_ai_controls"],
                        "customer_facing_ai": org_dict["customer_facing_ai"],
                        "ai_generated_content_reviewed": org_dict["ai_generated_content_reviewed"],
                        "ai_access_restricted": org_dict["ai_access_restricted"],
                        "ai_outputs_logged": org_dict["ai_outputs_logged"],
                        "automated_decisions": org_dict["automated_decisions"],
                        "automated_decision_types": org_dict["automated_decision_types"],
                        "data_types_processed": org_dict["data_types_processed"],
                        "trades_in_personal_info": org_dict["trades_in_personal_info"],
                        "has_data_retention_policy": org_dict["has_data_retention_policy"],
                        "data_retention_period": org_dict["data_retention_period"],
                        "consent_mechanism_exists": org_dict["consent_mechanism_exists"],
                        "vendor_dpa_in_place": org_dict["vendor_dpa_in_place"],
                        "pia_conducted": org_dict["pia_conducted"],
                        "has_privacy_policy": org_dict["has_privacy_policy"],
                        "vendor_ai_clauses_reviewed": org_dict["vendor_ai_clauses_reviewed"],
                        "existing_it_policies": org_dict["existing_it_policies"],
                        "incident_response_tested": org_dict["incident_response_tested"],
                        "board_ai_awareness": org_dict["board_ai_awareness"],
                        "training_frequency": org_dict["training_frequency"],
                        "ai_governance_contact": org_dict["ai_governance_contact"],
                        "ai_profiling_or_eligibility": org_dict["ai_profiling_or_eligibility"],
                        "bias_testing_conducted": org_dict["bias_testing_conducted"],
                        "ai_copyright_assessed": org_dict["ai_copyright_assessed"],
                        "ai_in_marketing": org_dict["ai_in_marketing"],
                        "human_review_available": org_dict["human_review_available"],
                        "vendor_audit_rights": org_dict["vendor_audit_rights"],
                        "ndb_ai_process": org_dict["ndb_ai_process"],
                        "ai_incident_register": org_dict["ai_incident_register"],
                        "essential_eight_applied": org_dict["essential_eight_applied"],
                        "ai_disclosure_to_customers": org_dict["ai_disclosure_to_customers"],
                        "ai_supply_chain_assessed": org_dict["ai_supply_chain_assessed"],
                        "tranche2_aware": org_dict["tranche2_aware"],
                        "data_overseas_mapped": org_dict["data_overseas_mapped"],
                    }
                    st.session_state.q_edit_org_id = org_id
                    st.session_state.q_step = 1
                    st.session_state.q_session_key = __import__("uuid").uuid4().hex
                    st.switch_page("pages/1_questionnaire.py")

    finally:
        db.close()

# --- Regulatory Update Feed (shown for logged-in users) ---
st.divider()
st.markdown("### Regulatory Updates")

_REG_UPDATES = [
    {
        "date": "Nov 2025",
        "title": "AI Safety Institute established with $29.9M funding",
        "detail": "The Australian AI Safety Institute will test AI systems, assess risks, and share findings. First reports expected mid-2026.",
        "tag": "Government",
        "color": "#16a34a",
    },
    {
        "date": "Dec 2024",
        "title": "Privacy Act penalties increased significantly",
        "detail": "POLA Act introduces 3-tier penalties: Tier 1 $330K, Tier 2 up to $3.3M, Tier 3 up to $50M or 30% of adjusted turnover. OAIC granted search-and-seizure powers.",
        "tag": "Privacy Act",
        "color": "#dc2626",
    },
    {
        "date": "Dec 2024",
        "title": "POLA Act 2024 receives Royal Assent",
        "detail": "Introduces statutory tort for serious invasion of privacy (commenced 10 June 2025) and automated decision transparency (commences 10 December 2026).",
        "tag": "POLA Act",
        "color": "#ea580c",
    },
    {
        "date": "Oct 2024",
        "title": "OAIC publishes AI and privacy expectations",
        "detail": "Guidance establishes OAIC expectations for organisations using AI, including PIA recommendations, Shadow AI controls, and cross-border data obligations.",
        "tag": "OAIC",
        "color": "#2563eb",
    },
    {
        "date": "2025-26",
        "title": "Privacy Act Review — Tranche 2 expected",
        "detail": "May remove the small business exemption, extending Privacy Act obligations to all organisations regardless of revenue. Prepare now.",
        "tag": "Reform",
        "color": "#7c3aed",
    },
]

for update in _REG_UPDATES:
    st.markdown(
        f"""
    <div style="background:#ffffff; border:1px solid #e2e8f0; border-left:4px solid {update["color"]}; border-radius:0 10px 10px 0; padding:14px 18px; margin-bottom:10px; box-shadow:0 1px 3px rgba(0,0,0,0.04);">
        <div style="display:flex; justify-content:space-between; align-items:center; margin-bottom:4px;">
            <span style="font-weight:700; color:#1a3c6e; font-size:0.95rem;">{update["title"]}</span>
            <span style="background:{update["color"]}15; color:{update["color"]}; padding:2px 10px; border-radius:20px; font-size:0.7rem; font-weight:600; border:1px solid {update["color"]}30">{update["tag"]}</span>
        </div>
        <div style="font-size:0.8rem; color:#64748b; margin-bottom:4px;">{update["date"]}</div>
        <div style="font-size:0.85rem; color:#334155;">{update["detail"]}</div>
    </div>
    """,
        unsafe_allow_html=True,
    )

if not has_org:
    # --- What This Tool Does ---
    st.markdown(
        """
    <div style="background:#f8fafc; border:1px solid #e2e8f0; border-radius:12px; padding:28px 32px; margin-bottom:24px;">
        <div style="font-size:1.25rem; font-weight:700; color:#1a3c6e; margin-bottom:12px;">
            What is this?
        </div>
        <div style="font-size:0.95rem; color:#334155; line-height:1.7;">
            This tool helps Australian businesses create AI governance policies that comply with
            the <strong>Privacy Act 1988</strong>, the <strong>POLA Act 2024</strong>, and current
            <strong>OAIC guidance</strong> on AI and privacy. It is designed for <strong>SMEs,
            enterprises, and consultants</strong> who use AI tools (chatbots, content generators,
            automated decision-making) and need compliant, boardroom-ready policy documents
            without hiring a specialist firm.
        </div>
    </div>
    """,
        unsafe_allow_html=True,
    )

    # --- How It Works ---
    st.markdown("### How It Works")

    col1, col2, col3 = st.columns(3)

    _steps = [
        (
            "1",
            "1. Answer the Questionnaire",
            "Complete a guided questionnaire covering your AI tools, data practices, vendor relationships, and governance posture. Takes about 10 minutes.",
        ),
        (
            "2",
            "2. Generate Policies",
            "The app recommends policies based on your profile and generates up to 19 regulation-aligned documents in PDF or Markdown, ready to customise and adopt.",
        ),
        (
            "3",
            "3. Review Compliance",
            "Get a scored compliance scorecard mapped to Australia's AI6 Essential Practices, with penalty exposure estimates and actionable remediation steps.",
        ),
    ]
    for col, (icon, title, desc) in zip([col1, col2, col3], _steps):
        with col:
            st.markdown(
                f"""
            <div style="background:#ffffff; border:1px solid #e2e8f0; border-radius:12px; padding:24px; text-align:center;
                        min-height:200px; display:flex; flex-direction:column; justify-content:center;
                        box-shadow:0 1px 4px rgba(0,0,0,0.05);">
                <div style="font-size:2rem; margin-bottom:8px;">{icon}</div>
                <div style="font-weight:700; color:#1a3c6e; margin-bottom:6px;">{title}</div>
                <div style="font-size:0.85rem; color:#64748b; line-height:1.5;">{desc}</div>
            </div>
            """,
                unsafe_allow_html=True,
            )

    st.markdown("")
    st.page_link("pages/1_questionnaire.py", label="Start Questionnaire →", use_container_width=True)

    # --- What You Get ---
    st.divider()
    st.markdown("### What You Get")

    wg1, wg2 = st.columns(2)
    with wg1:
        st.markdown(
            """
        <div style="background:#ffffff; border:1px solid #e2e8f0; border-radius:12px; padding:24px; min-height:240px;">
            <div style="font-weight:700; color:#1a3c6e; font-size:1.05rem; margin-bottom:12px;">Policy Documents (up to 19)</div>
            <div style="font-size:0.88rem; color:#334155; line-height:1.7;">
                <strong>Core Governance</strong> — AI Acceptable Use, Privacy Policy, Data Classification, Incident Response, Remediation Action Plan<br>
                <strong>Risk & Oversight</strong> — AI Ethics Framework, AI Risk Register, Bias Audit Procedure, Board AI Briefing, Employee AI Training Guide<br>
                <strong>Vendor & Supply Chain</strong> — Vendor Risk Assessment, AI Procurement & Tool Approval, AI Supply Chain Audit<br>
                <strong>Specialist</strong> — AI Transparency Statement, AI Data Retention, Shadow AI Playbook, Copyright & IP Policy, Statutory Tort Defence Brief, Tranche 2 Readiness Checklist
            </div>
        </div>
        """,
            unsafe_allow_html=True,
        )
    with wg2:
        st.markdown(
            """
        <div style="background:#ffffff; border:1px solid #e2e8f0; border-radius:12px; padding:24px; min-height:240px;">
            <div style="font-weight:700; color:#1a3c6e; font-size:1.05rem; margin-bottom:12px;">Compliance Scorecard</div>
            <div style="font-size:0.88rem; color:#334155; line-height:1.7;">
                <strong>Weighted scoring</strong> across 41 compliance checks mapped to Australia's AI6 Essential Practices<br>
                <strong>Penalty exposure estimate</strong> — regulatory fines under the Privacy Act and POLA Act, plus estimated breach costs<br>
                <strong>Gap analysis</strong> — critical, high, and medium gaps with specific remediation recommendations<br>
                <strong>Smart recommendations</strong> — policies are suggested based on your industry, size, AI usage, and risk profile<br>
                <strong>CSV export</strong> — download your questionnaire responses for internal records or auditor review
            </div>
        </div>
        """,
            unsafe_allow_html=True,
        )

    # --- Who It's For ---
    st.divider()
    st.markdown("### Who Is This For?")

    wf1, wf2, wf3 = st.columns(3)
    _audiences = [
        (
            "SMEs & Startups",
            "Small and medium businesses using AI tools like ChatGPT, Copilot, or automated customer support, who need compliant policies without a legal budget.",
        ),
        (
            "Enterprises",
            "Larger organisations preparing for POLA Act obligations, the removal of the small business exemption (Tranche 2), or board-level AI governance requirements.",
        ),
        (
            "Consultants & Advisors",
            "Privacy consultants, IT advisors, and legal professionals who want a structured starting point for client AI governance engagements.",
        ),
    ]
    for col, (title, desc) in zip([wf1, wf2, wf3], _audiences):
        with col:
            st.markdown(
                f"""
            <div style="background:#f8fafc; border:1px solid #e2e8f0; border-radius:12px; padding:20px; min-height:150px;">
                <div style="font-weight:700; color:#1a3c6e; margin-bottom:6px;">{title}</div>
                <div style="font-size:0.85rem; color:#475569; line-height:1.6;">{desc}</div>
            </div>
            """,
                unsafe_allow_html=True,
            )

    # --- Regulatory Alignment ---
    st.divider()
    st.markdown(
        """
    #### Regulatory Alignment
    All generated policies are aligned with:
    - **Privacy Act 1988** and Australian Privacy Principles (APPs 1-13)
    - **POLA Act 2024** — Statutory tort for serious privacy invasion (commenced Jun 2025) and automated decision transparency (commences Dec 2026)
    - **Australia's 8 AI Ethics Principles** and **AI6 Essential Practices** guidance
    - **OAIC Guidance** on AI and privacy expectations (Oct 2024)
    - **Australian Consumer Law** — obligations for AI-generated content and strict liability
    - **ACSC Essential Eight** — baseline cyber security controls for AI systems
    """
    )

    st.divider()
    st.caption(
        "**Disclaimer:** This tool provides general guidance and template documents to assist with AI governance. "
        "It does not constitute legal, financial, or professional advice. Organisations should seek independent "
        "legal counsel to ensure policies meet their specific regulatory obligations."
    )
