import io
import sys
import zipfile
from html import escape
from pathlib import Path

import streamlit as st

sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent))

from components.sidebar import render_sidebar

from app.database import SessionLocal, init_db
from app.models import Organisation, PolicyDocument

render_sidebar()
init_db()

st.title("Generated Policies")

if "org_id" not in st.session_state or not st.session_state.get("org_id"):
    st.warning("Please complete the questionnaire first.")
    st.stop()

org_id = st.session_state.org_id
db = SessionLocal()
try:
    org = db.query(Organisation).filter(Organisation.id == org_id).first()
    if org:
        st.write(f"Policies for **{org.business_name}**")

    policies = (
        db.query(PolicyDocument).filter(PolicyDocument.org_id == org_id).order_by(PolicyDocument.generated_at.desc()).all()
    )

    if not policies:
        st.info("No policies generated yet. Go to the Generate page to create some.")
        st.stop()

    template_labels = {
        "ai_acceptable_use": "AI Acceptable Use Policy",
        "privacy_policy": "Privacy Policy (APP-Compliant)",
        "data_classification": "Data Classification for AI",
        "incident_response": "AI Incident Response Plan",
        "remediation_action_plan": "Remediation Action Plan",
        "compliance_report": "Compliance Report",
        "vendor_risk_assessment": "AI Vendor Risk Assessment",
        "ai_ethics_framework": "AI Ethics & Fairness Framework",
        "employee_ai_training": "Employee AI Training Guide",
        "ai_risk_register": "AI Risk Register",
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

    _TYPE_COLORS = {
        "ai_acceptable_use": "#1a3c6e",
        "privacy_policy": "#7c3aed",
        "data_classification": "#2563eb",
        "incident_response": "#dc2626",
        "remediation_action_plan": "#ea580c",
        "compliance_report": "#16a34a",
        "vendor_risk_assessment": "#0891b2",
        "ai_ethics_framework": "#7c3aed",
        "employee_ai_training": "#16a34a",
        "ai_risk_register": "#ea580c",
        "board_ai_briefing": "#1a3c6e",
        "ai_transparency_statement": "#0891b2",
        "ai_data_retention": "#ea580c",
        "ai_procurement": "#16a34a",
        "shadow_ai_playbook": "#dc2626",
        "bias_audit_procedure": "#7c3aed",
        "statutory_tort_defence": "#ea580c",
        "tranche2_readiness": "#0891b2",
        "ai_tool_approval": "#2563eb",
        "essential_eight_ai": "#1a3c6e",
        "copyright_ip_policy": "#16a34a",
        "ai_supply_chain_audit": "#0891b2",
    }

    MIME_TYPES = {
        ".pdf": "application/pdf",
        ".docx": "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
        ".md": "text/markdown",
    }

    # --- Bulk Download ---
    _downloadable = [p for p in policies if Path(p.file_path).exists()]
    if len(_downloadable) > 1:
        zip_buf = io.BytesIO()
        with zipfile.ZipFile(zip_buf, "w", zipfile.ZIP_DEFLATED) as zf:
            for p in _downloadable:
                fp = Path(p.file_path)
                arcname = f"{template_labels.get(p.template_type, p.template_type)}_v{p.version}{fp.suffix}"
                zf.write(fp, arcname)
        zip_buf.seek(0)
        _safe_org = "".join(c if c.isalnum() or c in "-_ " else "" for c in (org.business_name if org else ""))[:80]
        st.download_button(
            label=f"Download All ({len(_downloadable)} files) as ZIP",
            data=zip_buf.getvalue(),
            file_name=f"{_safe_org}_policies.zip" if _safe_org else "policies.zip",
            mime="application/zip",
            use_container_width=True,
        )
        st.divider()

    for policy in policies:
        label = template_labels.get(policy.template_type, policy.template_type)
        color = _TYPE_COLORS.get(policy.template_type, "#1a3c6e")
        file_path = Path(policy.file_path)
        ext = file_path.suffix

        st.markdown(
            f"""
        <div class="policy-card" style="border-left:4px solid {color};">
            <div style="display:flex;justify-content:space-between;align-items:center;">
                <div>
                    <span class="policy-title">{label}</span>
                    <span class="version-badge" style="margin-left:10px;">v{policy.version}</span>
                </div>
                <span class="policy-hash">{escape((policy.content_hash or "")[:12]) or "—"}...</span>
            </div>
            <div class="policy-meta">Generated: {policy.generated_at.strftime("%Y-%m-%d %H:%M")} &nbsp;|&nbsp; Format: {ext.upper().strip(".")}</div>
        </div>
        """,
            unsafe_allow_html=True,
        )

        if file_path.exists():
            mime = MIME_TYPES.get(ext, "application/octet-stream")
            with open(file_path, "rb") as f:
                st.download_button(
                    label=f"Download {ext.upper().strip('.')}",
                    data=f.read(),
                    file_name=file_path.name,
                    mime=mime,
                    key=f"dl_{policy.id}",
                    use_container_width=True,
                )
        else:
            st.warning("File missing")

        # View content — only for markdown files
        if file_path.exists() and ext == ".md":
            with st.expander("View Full Document"):
                content = file_path.read_text(encoding="utf-8")
                st.text(content)

finally:
    db.close()
