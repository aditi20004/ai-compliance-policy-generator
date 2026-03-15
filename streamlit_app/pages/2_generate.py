import sys
from pathlib import Path

import streamlit as st

sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent))

from components.sidebar import render_sidebar

from app.audit import log_event
from app.database import SessionLocal, init_db
from app.generator import generate_policy
from app.models import Organisation, PolicyDocument, org_to_dict

render_sidebar()
init_db()

st.title("Generate Policy Documents")

if "org_id" not in st.session_state or not st.session_state.get("org_id"):
    st.warning("Please complete the questionnaire first.")
    st.stop()

org_id = st.session_state.org_id

db = SessionLocal()
try:
    org = db.query(Organisation).filter(Organisation.id == org_id).first()

    if not org:
        st.error("Organisation not found. Please complete the questionnaire again.")
        st.stop()

    st.write(f"Generating policies for **{org.business_name}**")

    template_labels = {
        "ai_acceptable_use": "AI Acceptable Use Policy",
        "data_classification": "Data Classification for AI",
        "incident_response": "AI Incident Response Plan",
        "remediation_action_plan": "Remediation Action Plan",
        "vendor_risk_assessment": "AI Vendor Risk Assessment",
        "ai_ethics_framework": "AI Ethics & Fairness Framework",
        "employee_ai_training": "Employee AI Training Guide",
        "ai_risk_register": "AI Risk Register",
        "privacy_policy": "Privacy Policy (APP-Compliant)",
        "board_ai_briefing": "Board AI Risk Briefing",
        "ai_transparency_statement": "AI Transparency Statement",
        "ai_data_retention": "AI Data Retention & Destruction Policy",
        "ai_procurement": "AI Procurement Policy",
        "shadow_ai_playbook": "Shadow AI Detection & Response Playbook",
        "bias_audit_procedure": "AI Bias & Fairness Audit Procedure",
        "statutory_tort_defence": "Statutory Tort Defence Checklist",
        "tranche2_readiness": "POLA Act Tranche 2 Readiness Plan",
        "ai_tool_approval": "AI Tool Approval & Onboarding Process",
        "essential_eight_ai": "Essential Eight Controls for AI",
        "copyright_ip_policy": "AI Copyright & IP Policy",
        "ai_supply_chain_audit": "AI Supply Chain Audit Template",
    }

    # Core policy templates shown on this page; remediation + compliance report generated from the Compliance page
    _generate_page_templates = [
        "ai_acceptable_use",
        "privacy_policy",
        "data_classification",
        "incident_response",
        "vendor_risk_assessment",
        "ai_ethics_framework",
        "employee_ai_training",
        "ai_risk_register",
        "board_ai_briefing",
        "ai_transparency_statement",
        "ai_data_retention",
        "ai_procurement",
        "shadow_ai_playbook",
        "bias_audit_procedure",
        "statutory_tort_defence",
        "tranche2_readiness",
        "ai_tool_approval",
        "essential_eight_ai",
        "copyright_ip_policy",
        "ai_supply_chain_audit",
    ]

    # Accept pre-selection from Compliance page "Fix this" buttons
    _preselect = st.session_state.get("preselect_templates")
    _default = _preselect if _preselect else _generate_page_templates

    selected_templates = st.multiselect(
        "Select policy documents to generate:",
        options=_generate_page_templates,
        default=_default,
        format_func=lambda x: template_labels.get(x, x),
    )
    # Clear preselection after widget is created (so user changes persist)
    st.session_state.pop("preselect_templates", None)

    output_format = st.selectbox(
        "Output format:",
        options=["pdf", "markdown"],
        index=0,
        format_func=lambda x: x.upper(),
    )

    from app.config import settings

    has_api_key = bool(settings.anthropic_api_key)
    with st.container(border=True):
        st.markdown("**AI Enhancement**")
        enhance_llm = st.checkbox(
            "Enhance with AI regulatory alignment notes",
            value=False,
            disabled=not has_api_key,
            help="Uses AI + RAG to append tailored regulatory alignment notes to each policy."
            + ("" if has_api_key else " (Set ANTHROPIC_API_KEY in .env to enable)"),
        )
        st.caption(
            "When enabled, AI analyses your questionnaire responses and appends tailored regulatory alignment notes to each generated policy."
            if has_api_key
            else "Set your API key in .env to unlock AI-enhanced policy generation."
        )

    if st.button("Generate Policies", type="primary", use_container_width=True):
        if not selected_templates:
            st.warning("Please select at least one template.")
        else:
            questionnaire_data = org_to_dict(org)

            for template_type in selected_templates:
                try:
                    with st.spinner(f"Generating {template_labels[template_type]}..."):
                        # Board briefing needs policy_types context
                        if template_type == "board_ai_briefing":
                            from app.generator import build_board_briefing_context

                            existing_policies = db.query(PolicyDocument).filter(PolicyDocument.org_id == org.id).all()
                            policy_types = {p.template_type for p in existing_policies}
                            from app.generator import render_policy_text, save_policy_markdown, save_policy_pdf

                            context = build_board_briefing_context(questionnaire_data, policy_types)
                            content = render_policy_text(template_type, context)
                            if output_format == "pdf":
                                file_path, content_hash = save_policy_pdf(template_type, content, org.id)
                            else:
                                file_path, content_hash = save_policy_markdown(template_type, content, org.id)
                        else:
                            file_path, content_hash = generate_policy(
                                template_type,
                                questionnaire_data,
                                org.id,
                                output_format,
                                enhance_with_llm=enhance_llm,
                            )

                        existing_count = (
                            db.query(PolicyDocument)
                            .filter(
                                PolicyDocument.org_id == org.id,
                                PolicyDocument.template_type == template_type,
                            )
                            .count()
                        )

                        policy = PolicyDocument(
                            org_id=org.id,
                            template_type=template_type,
                            version=existing_count + 1,
                            file_path=file_path,
                            content_hash=content_hash,
                            status="generated",
                        )
                        db.add(policy)
                        db.commit()

                        log_event(
                            db,
                            event_type="policy_generated",
                            org_id=org.id,
                            metadata={
                                "template_type": template_type,
                                "version": policy.version,
                                "format": output_format,
                            },
                            content_hash=content_hash,
                        )

                        st.markdown(
                            f"""
                        <div class="section-card" style="border-left:4px solid #16a34a;">
                            <div style="display:flex;align-items:center;gap:10px;">
                                <span style="color:#16a34a;font-size:1.2rem;font-weight:bold;">Done</span>
                                <span style="font-weight:600;color:#1a3c6e;">{template_labels[template_type]}</span>
                                <span class="version-badge" style="background:#f0fdf4;color:#16a34a;border-color:#16a34a20;">v{policy.version}</span>
                                <span style="color:#64748b;font-size:0.8rem;">{output_format.upper()}</span>
                            </div>
                        </div>
                        """,
                            unsafe_allow_html=True,
                        )
                except Exception as e:
                    db.rollback()
                    st.error(f"Failed to generate {template_labels[template_type]}: {e}")

            st.info("Navigate to the **Policies** page to download your documents.")

finally:
    db.close()
