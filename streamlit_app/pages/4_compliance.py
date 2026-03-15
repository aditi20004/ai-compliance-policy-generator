import datetime
import hashlib
import sys
from pathlib import Path

import plotly.graph_objects as go
import streamlit as st

sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent))

from components.sidebar import render_sidebar

from app.compliance_checker import calculate_compliance_score, get_industry_benchmarks, save_compliance_snapshot
from app.database import SessionLocal, init_db
from app.models import ComplianceEvidence, Organisation, PolicyDocument, RemediationAction, org_to_dict

# Map checklist gap names to the template that fixes them
_GAP_TO_TEMPLATE = {
    "AI acceptable use policy exists": "ai_acceptable_use",
    "Data classification rules defined": "data_classification",
    "Incident response plan exists": "incident_response",
    "Vendor Data Processing Agreements in place": "vendor_risk_assessment",
    "Published privacy policy": "privacy_policy",
    "POLA Act automated decision disclosure ready": "privacy_policy",
    "Staff AI training scheduled": "employee_ai_training",
    "Training frequency meets OAIC recommendation": "employee_ai_training",
    "Board/executive AI awareness": "board_ai_briefing",
    "Privacy Impact Assessment conducted": "ai_ethics_framework",
    "Data retention policy for AI outputs": "data_classification",
    "AI tool register maintained": "ai_acceptable_use",
    "Cross-border data flows mapped": "vendor_risk_assessment",
    "Human oversight for high-impact AI decisions": "ai_ethics_framework",
    "Existing IT security policies foundation": "ai_acceptable_use",
    "Shadow AI controls in place": "shadow_ai_playbook",
    "AI prompts and outputs logged": "ai_acceptable_use",
    "Consent mechanisms for AI data processing": "privacy_policy",
    "ACL compliance for AI-generated content": "ai_ethics_framework",
    "AI access restricted by role": "ai_acceptable_use",
    "Vendor AI clauses reviewed": "vendor_risk_assessment",
    "Data minimisation practices for AI": "data_classification",
    "Bias and fairness testing conducted": "bias_audit_procedure",
    "NDB scheme — AI breach notification process": "incident_response",
    "Essential Eight controls applied to AI systems": "essential_eight_ai",
    "AI incident register maintained": "incident_response",
    "APP 5 — Notification of AI data collection": "privacy_policy",
    "APP 7 — Direct marketing consent for AI-generated communications": "privacy_policy",
    "AI use disclosed to customers": "ai_transparency_statement",
    "APP 2 — Anonymity/pseudonymity option for AI interactions": "privacy_policy",
    "APP 10 — Quality assurance for AI-processed data": "ai_ethics_framework",
    "APP 12 — Access to AI-processed personal information": "privacy_policy",
    "APP 13 — Correction of AI-processed personal information": "privacy_policy",
    "AI supply chain assessed": "ai_supply_chain_audit",
    "Vendor audit rights in AI contracts": "ai_supply_chain_audit",
    "Copyright and IP risk assessed for AI outputs": "copyright_ip_policy",
    "POLA Act Tranche 2 awareness": "tranche2_readiness",
    "Cross-border data flows mapped for AI tools": "vendor_risk_assessment",
    "Named AI governance contact": "ai_acceptable_use",
}

_TEMPLATE_LABELS = {
    "ai_acceptable_use": "AI Acceptable Use Policy",
    "data_classification": "Data Classification Policy",
    "incident_response": "Incident Response Plan",
    "vendor_risk_assessment": "Vendor Risk Assessment",
    "privacy_policy": "Privacy Policy",
    "employee_ai_training": "Employee AI Training Guide",
    "board_ai_briefing": "Board AI Briefing",
    "ai_ethics_framework": "AI Ethics Framework",
    "ai_risk_register": "AI Risk Register",
    "ai_transparency_statement": "AI Transparency Statement",
    "ai_data_retention": "AI Data Retention & Destruction Policy",
    "ai_procurement": "AI Procurement Policy",
    "shadow_ai_playbook": "Shadow AI Playbook",
    "bias_audit_procedure": "Bias & Fairness Audit Procedure",
    "statutory_tort_defence": "Statutory Tort Defence Checklist",
    "tranche2_readiness": "Tranche 2 Readiness Plan",
    "ai_tool_approval": "AI Tool Approval Process",
    "essential_eight_ai": "Essential Eight for AI",
    "copyright_ip_policy": "Copyright & IP Policy",
    "ai_supply_chain_audit": "Supply Chain Audit Template",
}

render_sidebar()
init_db()

st.title("AI Compliance Scorecard")

if "org_id" not in st.session_state or not st.session_state.get("org_id"):
    st.warning("Please complete the questionnaire first.")
    st.stop()

org_id = st.session_state.org_id
db = SessionLocal()
try:
    org = db.query(Organisation).filter(Organisation.id == org_id).first()
    if not org:
        st.error("Organisation not found.")
        st.stop()

    st.write(f"Compliance assessment for **{org.business_name}**")

    policies = db.query(PolicyDocument).filter(PolicyDocument.org_id == org_id).all()
    policy_types = {p.template_type for p in policies}

    org_data = org_to_dict(org)

    result = calculate_compliance_score(org_data, policy_types)

    # Save snapshot for benchmarking (once per session)
    if f"snapshot_saved_{org_id}" not in st.session_state:
        save_compliance_snapshot(db, org_id, org_data["industry"], result)
        st.session_state[f"snapshot_saved_{org_id}"] = True

    # --- Load evidence for this org ---
    all_evidence = db.query(ComplianceEvidence).filter(ComplianceEvidence.org_id == org_id).all()
    evidence_by_item = {}
    for ev in all_evidence:
        evidence_by_item.setdefault(ev.checklist_item_name, []).append(ev)

    # Count evidence-backed items
    items_with_evidence = set(evidence_by_item.keys())
    passed_items = [item for item in result["checklist"] if item["passed"]]
    evidence_backed_count = sum(1 for item in passed_items if item["name"] in items_with_evidence)
    self_attested_count = len(passed_items) - evidence_backed_count

    # --- Export Buttons ---
    col_btn1, col_btn2 = st.columns(2)

    with col_btn1:
        if st.button("Download Compliance Report as PDF", type="primary", use_container_width=True):
            from app.audit import log_event
            from app.generator import generate_compliance_report_pdf
            from app.models import PolicyDocument as PD

            try:
                file_path, content_hash = generate_compliance_report_pdf(org_data, result, org_id)
                existing = db.query(PD).filter(PD.org_id == org_id, PD.template_type == "compliance_report").count()
                policy = PD(
                    org_id=org_id,
                    template_type="compliance_report",
                    version=existing + 1,
                    file_path=file_path,
                    content_hash=content_hash,
                    status="generated",
                )
                db.add(policy)
                try:
                    db.commit()
                except Exception:
                    db.rollback()
                    _fp = Path(file_path)
                    if _fp.exists():
                        _fp.unlink(missing_ok=True)
                    raise
                log_event(
                    db,
                    event_type="policy_generated",
                    org_id=org_id,
                    metadata={"template_type": "compliance_report", "format": "pdf"},
                    content_hash=content_hash,
                )
                with open(file_path, "rb") as f:
                    st.session_state["_compliance_report_pdf"] = f.read()
                    _safe_name = "".join(c if c.isalnum() or c in "-_ " else "" for c in org.business_name)[:80]
                    st.session_state["_compliance_report_name"] = f"compliance_report_{_safe_name}.pdf"
            except Exception as e:
                st.error(f"Failed to generate compliance report: {e}")

    # Persist download button outside the if-block so it survives reruns
    if st.session_state.get("_compliance_report_pdf"):
        with col_btn1:
            st.download_button(
                label="Save Compliance Report PDF",
                data=st.session_state["_compliance_report_pdf"],
                file_name=st.session_state.get("_compliance_report_name", "compliance_report.pdf"),
                mime="application/pdf",
                key="dl_compliance_report",
            )

    with col_btn2:
        if st.button("Generate Remediation Action Plan", use_container_width=True):
            from app.audit import log_event
            from app.generator import build_remediation_context, render_policy_text, save_policy_pdf
            from app.models import PolicyDocument as PD

            try:
                context = build_remediation_context(org_data, result)
                content = render_policy_text("remediation_action_plan", context)
                file_path, content_hash = save_policy_pdf("remediation_action_plan", content, org_id)
                existing = db.query(PD).filter(PD.org_id == org_id, PD.template_type == "remediation_action_plan").count()
                policy = PD(
                    org_id=org_id,
                    template_type="remediation_action_plan",
                    version=existing + 1,
                    file_path=file_path,
                    content_hash=content_hash,
                    status="generated",
                )
                db.add(policy)
                try:
                    db.commit()
                except Exception:
                    db.rollback()
                    _fp = Path(file_path)
                    if _fp.exists():
                        _fp.unlink(missing_ok=True)
                    raise
                log_event(
                    db,
                    event_type="policy_generated",
                    org_id=org_id,
                    metadata={"template_type": "remediation_action_plan", "format": "pdf"},
                    content_hash=content_hash,
                )
                with open(file_path, "rb") as f:
                    st.session_state["_remediation_pdf"] = f.read()
                    _safe_rname = "".join(c if c.isalnum() or c in "-_ " else "" for c in org.business_name)[:80]
                    st.session_state["_remediation_name"] = f"remediation_plan_{_safe_rname}.pdf"
            except Exception as e:
                st.error(f"Failed to generate remediation plan: {e}")

    # Persist download button outside the if-block so it survives reruns
    if st.session_state.get("_remediation_pdf"):
        with col_btn2:
            st.download_button(
                label="Save Remediation Plan PDF",
                data=st.session_state["_remediation_pdf"],
                file_name=st.session_state.get("_remediation_name", "remediation_plan.pdf"),
                mime="application/pdf",
                key="dl_remediation_plan",
            )

    st.divider()

    # --- Top-level metrics with dual scores ---
    score = result["score_percentage"]
    risk = result["risk_rating"]

    col1, col2, col3, col4 = st.columns(4)

    with col1:
        if score >= 80:
            st.metric("Compliance Score", f"{score}%", delta="Good")
        elif score >= 60:
            st.metric("Compliance Score", f"{score}%", delta="Needs Work", delta_color="off")
        elif score >= 40:
            st.metric("Compliance Score", f"{score}%", delta="High Risk", delta_color="inverse")
        else:
            st.metric("Compliance Score", f"{score}%", delta="Critical", delta_color="inverse")

    with col2:
        st.metric("Items Passed", f"{result['passed']}/{result['total']}")

    with col3:
        risk_colors = {"LOW": "green", "MEDIUM": "orange", "HIGH": "red", "CRITICAL": "red"}
        color = risk_colors.get(risk, "gray")
        st.markdown("**Risk Rating**")
        st.markdown(f":{color}[**{risk}**]")

    with col4:
        st.metric("Evidence-Backed", f"{evidence_backed_count}/{len(passed_items)}")
        if self_attested_count > 0:
            st.caption(f"{self_attested_count} self-attested")

    st.caption(result["risk_description"])

    # --- Evidence Assurance Bar ---
    if passed_items:
        ev_pct = round((evidence_backed_count / len(passed_items)) * 100) if passed_items else 0
        st.progress(ev_pct / 100, text=f"Evidence assurance: {ev_pct}% of passed items have supporting documents")

    # --- AI6 Radar Chart + Risk Heatmap ---
    st.divider()
    col_radar, col_heat = st.columns(2)

    with col_radar:
        st.subheader("AI6 Practice Radar")

        practice_names = []
        practice_scores = []
        for practice_name_key, practice_data in result["by_practice"].items():
            short = practice_name_key.split(". ", 1)[1] if ". " in practice_name_key else practice_name_key
            practice_names.append(short)
            pct = round((practice_data["passed"] / practice_data["total"]) * 100) if practice_data["total"] > 0 else 0
            practice_scores.append(pct)

        radar_names = practice_names + [practice_names[0]]
        radar_scores = practice_scores + [practice_scores[0]]

        fig_radar = go.Figure()
        fig_radar.add_trace(
            go.Scatterpolar(
                r=radar_scores,
                theta=radar_names,
                fill="toself",
                fillcolor="rgba(26, 60, 110, 0.15)",
                line=dict(color="#1a3c6e", width=2.5),
                marker=dict(size=7, color="#1a3c6e"),
                name="Your Score",
            )
        )
        fig_radar.add_trace(
            go.Scatterpolar(
                r=[100] * len(radar_names),
                theta=radar_names,
                line=dict(color="#e2e8f0", width=1, dash="dot"),
                marker=dict(size=0),
                name="Full Compliance",
                showlegend=True,
            )
        )
        fig_radar.update_layout(
            polar=dict(
                radialaxis=dict(visible=True, range=[0, 100], tickfont=dict(size=10), gridcolor="#e2e8f0"),
                angularaxis=dict(tickfont=dict(size=11, color="#1a3c6e")),
                bgcolor="rgba(0,0,0,0)",
            ),
            showlegend=True,
            legend=dict(orientation="h", yanchor="bottom", y=-0.15, xanchor="center", x=0.5, font=dict(size=10)),
            height=380,
            margin=dict(l=60, r=60, t=30, b=40),
            paper_bgcolor="rgba(0,0,0,0)",
        )
        st.plotly_chart(fig_radar, use_container_width=True)

    with col_heat:
        st.subheader("Risk Heatmap")

        severity_order = ["critical", "high", "medium", "low"]
        severity_labels = ["Critical", "High", "Medium", "Low"]
        heatmap_data = []
        heatmap_practices = []

        for practice_name_key, practice_data in result["by_practice"].items():
            short = practice_name_key.split(". ", 1)[1] if ". " in practice_name_key else practice_name_key
            heatmap_practices.append(short)
            row = []
            for sev in severity_order:
                count = sum(1 for item in practice_data["items"] if not item["passed"] and item["severity"] == sev)
                row.append(count)
            heatmap_data.append(row)

        fig_heat = go.Figure(
            data=go.Heatmap(
                z=heatmap_data,
                x=severity_labels,
                y=heatmap_practices,
                colorscale=[[0, "#f0fdf4"], [0.25, "#fef9c3"], [0.5, "#fed7aa"], [0.75, "#fca5a5"], [1, "#dc2626"]],
                showscale=True,
                colorbar=dict(title="Gaps", titleside="right", tickvals=[0, 1, 2, 3], len=0.8),
                text=heatmap_data,
                texttemplate="%{text}",
                textfont=dict(size=14, color="#1a1a2e"),
                hovertemplate="Practice: %{y}<br>Severity: %{x}<br>Gaps: %{z}<extra></extra>",
            )
        )
        fig_heat.update_layout(
            xaxis=dict(title="", tickfont=dict(size=11)),
            yaxis=dict(title="", tickfont=dict(size=11), autorange="reversed"),
            height=380,
            margin=dict(l=10, r=10, t=30, b=10),
            paper_bgcolor="rgba(0,0,0,0)",
        )
        st.plotly_chart(fig_heat, use_container_width=True)

    # --- Penalty Exposure ---
    st.divider()
    st.subheader("Estimated Maximum Penalty Exposure")

    penalty = result["penalty_exposure"]
    total_exposure = penalty["total_maximum_exposure"]

    if total_exposure > 0:
        st.error(f"**Total maximum exposure: ${total_exposure:,.0f} AUD**")

        # Regulatory penalties (enforceable by OAIC / ACCC)
        reg_items = penalty.get("regulatory_items", {})
        if reg_items:
            st.markdown("**Regulatory Penalties** (enforceable fines)")
            for item_name, amount in reg_items.items():
                if item_name == "Note":
                    st.info(amount)
                else:
                    st.write(f"- **{item_name}**: ${amount:,.0f}")

        # Estimated business costs (not fines)
        est_items = penalty.get("estimated_items", {})
        if est_items:
            st.markdown("**Estimated Business Costs** (not regulatory fines)")
            for item_name, amount in est_items.items():
                st.write(f"- **{item_name}**: ${amount:,.0f}")
            st.caption("Sources: IBM 2025 Cost of a Data Breach Report; ALRC Report 123. "
                       "Estimates scaled for Australian SMEs. Actual costs may vary.")

        # Penalty stacking warning
        stacking_note = penalty.get("stacking_note")
        if stacking_note:
            st.warning(stacking_note)

        if penalty["is_privacy_act_covered"]:
            st.caption("Organisation is covered by the Privacy Act 1988 (revenue > $3M or trades in personal information).")
        else:
            st.caption("Small business exemption currently applies, but statutory tort and ACL obligations still apply.")
    else:
        st.success("No significant penalty exposure identified based on current profile.")

    # --- Industry Comparison ---
    st.divider()
    st.subheader("Industry Comparison")

    benchmarks = get_industry_benchmarks(db, org_data["industry"], result["score_percentage"])

    col_b1, col_b2, col_b3 = st.columns(3)
    with col_b1:
        st.metric("Your Score", f"{result['score_percentage']}%")
    with col_b2:
        st.metric(
            "Industry Average",
            f"{benchmarks['avg_score']}%",
            delta=f"{benchmarks['gap_from_average']:+.1f}%",
            delta_color="normal",
        )
    with col_b3:
        st.metric("Percentile Rank", f"{benchmarks['percentile_rank']}th")

    st.caption(f"Based on {benchmarks['org_count']} organisations in the **{org_data['industry']}** sector.")

    st.write("**Score Distribution**")
    dist = benchmarks["score_distribution"]
    dist_labels = list(dist.keys())
    dist_values = list(dist.values())

    if score <= 25:
        org_bucket_idx = 0
    elif score <= 50:
        org_bucket_idx = 1
    elif score <= 75:
        org_bucket_idx = 2
    else:
        org_bucket_idx = 3

    bar_colors = ["#cbd5e1"] * 4
    bar_colors[org_bucket_idx] = "#1a3c6e"

    fig_dist = go.Figure(
        data=[
            go.Bar(
                x=dist_labels,
                y=dist_values,
                marker_color=bar_colors,
                text=dist_values,
                textposition="outside",
                textfont=dict(size=12, color="#1a3c6e"),
            )
        ]
    )
    fig_dist.update_layout(
        xaxis=dict(title="Score Range"),
        yaxis=dict(title="Organisations", dtick=1),
        height=250,
        margin=dict(l=40, r=20, t=10, b=40),
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(0,0,0,0)",
    )
    st.plotly_chart(fig_dist, use_container_width=True)

    # --- AI6 Practice Breakdown with Evidence Upload ---
    st.divider()
    st.subheader("AI6 Essential Practices Breakdown")

    EVIDENCE_DIR = Path(__file__).resolve().parent.parent.parent / "data" / "evidence"
    EVIDENCE_DIR.mkdir(parents=True, exist_ok=True)

    for practice_name, practice_data in result["by_practice"].items():
        p_passed = practice_data["passed"]
        p_total = practice_data["total"]
        pct = round((p_passed / p_total) * 100) if p_total > 0 else 0

        if pct == 100:
            icon = "white_check_mark"
        elif pct >= 50:
            icon = "warning"
        else:
            icon = "x"

        with st.expander(f":{icon}: {practice_name} ({p_passed}/{p_total} passed)", expanded=(pct < 100)):
            for item in practice_data["items"]:
                status = "white_check_mark" if item["passed"] else "x"
                severity_badge = ""
                if not item["passed"]:
                    sev = item["severity"]
                    if sev == "critical":
                        severity_badge = " :red[CRITICAL]"
                    elif sev == "high":
                        severity_badge = " :orange[HIGH]"
                    elif sev == "medium":
                        severity_badge = " :blue[MEDIUM]"
                    else:
                        severity_badge = " LOW"

                # Evidence indicator
                item_evidence = evidence_by_item.get(item["name"], [])
                ev_badge = f" :green[({len(item_evidence)} evidence)]" if item_evidence else ""

                st.markdown(f":{status}: **{item['name']}**{severity_badge}{ev_badge}")
                st.caption(f"{item['description']}")
                st.caption(f"Regulation: {item['regulation']} | Weight: {item['weight']}/10")

                if not item["passed"] and item.get("recommendation"):
                    st.info(f"Recommendation: {item['recommendation']}")

                # Show existing evidence
                if item_evidence:
                    for ev in item_evidence:
                        ecol1, ecol2, ecol3 = st.columns([4, 1, 1])
                        with ecol1:
                            st.caption(
                                f"  Attached: **{ev.file_name}** — {ev.uploaded_at.strftime('%Y-%m-%d %H:%M')}"
                                + (f" | Note: {ev.notes}" if ev.notes else "")
                            )
                        with ecol2:
                            ev_path = Path(ev.file_path).resolve()
                            if not ev_path.is_relative_to(EVIDENCE_DIR.resolve()):
                                st.caption("Invalid path")
                            elif ev_path.exists():
                                with open(ev_path, "rb") as dl_f:
                                    st.download_button(
                                        label="Download",
                                        data=dl_f.read(),
                                        file_name=ev.file_name,
                                        key=f"dl_ev_{ev.id}",
                                        use_container_width=True,
                                    )
                            else:
                                st.caption("File missing")
                        with ecol3:
                            confirm_key = f"confirm_rm_{ev.id}"
                            if st.session_state.get(confirm_key):
                                st.warning(f"Delete **{ev.file_name}**?")
                                c1, c2 = st.columns(2)
                                with c1:
                                    if st.button("Yes, delete", key=f"yes_rm_{ev.id}", type="primary"):
                                        try:
                                            Path(ev.file_path).unlink(missing_ok=True)
                                        except Exception:
                                            pass
                                        db.delete(ev)
                                        db.commit()
                                        st.session_state.pop(confirm_key, None)
                                        st.rerun()
                                with c2:
                                    if st.button("Cancel", key=f"cancel_rm_{ev.id}"):
                                        st.session_state.pop(confirm_key, None)
                                        st.rerun()
                            else:
                                if st.button("Remove", key=f"rm_ev_{ev.id}", type="secondary"):
                                    st.session_state[confirm_key] = True
                                    st.rerun()

                # Upload evidence
                safe_key = item["name"].replace(" ", "_").replace("(", "").replace(")", "")[:30]
                _MAX_UPLOAD_MB = 10
                uploaded = st.file_uploader(
                    f"Upload evidence for: {item['name']}",
                    type=["pdf", "png", "jpg", "docx", "xlsx", "csv", "txt"],
                    key=f"ev_upload_{safe_key}_{org_id}",
                    label_visibility="collapsed",
                )
                if uploaded:
                    file_bytes = uploaded.getbuffer()
                    file_hash = hashlib.sha256(file_bytes).hexdigest()

                    # Prevent duplicate uploads on Streamlit rerun
                    ev_upload_key = f"_ev_saved_{org_id}_{safe_key}_{file_hash[:16]}"
                    if st.session_state.get(ev_upload_key):
                        pass  # Already saved this file
                    else:
                        _upload_valid = True
                        # Validate file size (10 MB limit)
                        if len(file_bytes) > _MAX_UPLOAD_MB * 1024 * 1024:
                            st.error(f"File too large. Maximum size is {_MAX_UPLOAD_MB} MB.")
                            _upload_valid = False

                        import mimetypes

                        file_ext = Path(uploaded.name).suffix.lower()
                        _ALLOWED_EXTENSIONS = {".pdf", ".png", ".jpg", ".jpeg", ".docx", ".xlsx", ".csv", ".txt"}
                        if _upload_valid and file_ext not in _ALLOWED_EXTENSIONS:
                            st.error(f"File type `{file_ext}` is not allowed.")
                            _upload_valid = False

                        if _upload_valid:
                            guessed_type = mimetypes.guess_type(uploaded.name)[0] or ""
                            _ALLOWED_MIMES = {
                                "application/pdf",
                                "image/png",
                                "image/jpeg",
                                "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
                                "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                                "text/csv",
                                "text/plain",
                            }
                            if guessed_type and guessed_type not in _ALLOWED_MIMES:
                                st.error(f"File MIME type `{guessed_type}` is not allowed.")
                                _upload_valid = False

                        if _upload_valid:
                            import uuid

                            safe_filename = f"{org_id}_{safe_key}_{uuid.uuid4().hex[:12]}{file_ext}"
                            file_path = EVIDENCE_DIR / safe_filename
                            with open(file_path, "wb") as f:
                                f.write(file_bytes)

                            ev_record = ComplianceEvidence(
                                org_id=org_id,
                                checklist_item_name=item["name"],
                                file_path=str(file_path),
                                file_name=uploaded.name,
                                file_hash=file_hash,
                            )
                            db.add(ev_record)
                            db.commit()
                            st.session_state[ev_upload_key] = True
                            st.success(f"Evidence uploaded: {uploaded.name}")
                            st.rerun()

                st.markdown("---")

    # --- Critical Gaps Summary ---
    if result["critical_gaps"] or result["high_gaps"]:
        st.divider()
        st.subheader("Priority Actions Required")

        # Auto-create remediation actions for gaps if they don't exist yet
        existing_actions = db.query(RemediationAction).filter(RemediationAction.org_id == org_id).all()
        existing_action_names = {a.checklist_item_name for a in existing_actions}

        new_actions_created = False
        today = datetime.date.today()
        for gap in result["critical_gaps"]:
            if gap["name"] not in existing_action_names:
                action = RemediationAction(
                    org_id=org_id,
                    checklist_item_name=gap["name"],
                    action_description=gap["recommendation"],
                    severity="critical",
                    deadline=datetime.datetime.combine(today + datetime.timedelta(days=30), datetime.time()),
                )
                db.add(action)
                new_actions_created = True

        for gap in result["high_gaps"]:
            if gap["name"] not in existing_action_names:
                action = RemediationAction(
                    org_id=org_id,
                    checklist_item_name=gap["name"],
                    action_description=gap["recommendation"],
                    severity="high",
                    deadline=datetime.datetime.combine(today + datetime.timedelta(days=60), datetime.time()),
                )
                db.add(action)
                new_actions_created = True

        # Also add medium/low gaps
        medium_low_gaps = [
            item for item in result["checklist"] if not item["passed"] and item["severity"] in ("medium", "low")
        ]
        for gap in medium_low_gaps:
            if gap["name"] not in existing_action_names:
                days = 90 if gap["severity"] == "medium" else 120
                action = RemediationAction(
                    org_id=org_id,
                    checklist_item_name=gap["name"],
                    action_description=gap["recommendation"],
                    severity=gap["severity"],
                    deadline=datetime.datetime.combine(today + datetime.timedelta(days=days), datetime.time()),
                )
                db.add(action)
                new_actions_created = True

        if new_actions_created:
            db.commit()

        if result["critical_gaps"]:
            st.error(f"**{len(result['critical_gaps'])} Critical Gap(s) - Immediate Action Required**")
            for _ci, gap in enumerate(result["critical_gaps"], 1):
                fix_template = _GAP_TO_TEMPLATE.get(gap["name"])
                gcol1, gcol2 = st.columns([4, 1])
                with gcol1:
                    st.write(f"{_ci}. **{gap['name']}** ({gap['regulation']})")
                    st.caption(f"   {gap['recommendation']}")
                with gcol2:
                    if fix_template:
                        fix_label = _TEMPLATE_LABELS.get(fix_template, fix_template)
                        _gap_key = hashlib.md5(gap["name"].encode()).hexdigest()[:12]
                        if st.button(f"Generate {fix_label}", key=f"fix_crit_{_gap_key}", use_container_width=True):
                            st.session_state["preselect_templates"] = [fix_template]
                            st.switch_page("pages/2_generate.py")

        if result["high_gaps"]:
            st.warning(f"**{len(result['high_gaps'])} High Priority Gap(s)**")
            for gap in result["high_gaps"]:
                fix_template = _GAP_TO_TEMPLATE.get(gap["name"])
                gcol1, gcol2 = st.columns([4, 1])
                with gcol1:
                    st.write(f"- **{gap['name']}** ({gap['regulation']})")
                    st.caption(f"   {gap['recommendation']}")
                with gcol2:
                    if fix_template:
                        fix_label = _TEMPLATE_LABELS.get(fix_template, fix_template)
                        _gap_key = hashlib.md5(gap["name"].encode()).hexdigest()[:12]
                        if st.button(f"Generate {fix_label}", key=f"fix_high_{_gap_key}", use_container_width=True):
                            st.session_state["preselect_templates"] = [fix_template]
                            st.switch_page("pages/2_generate.py")

        st.page_link("pages/7_actions.py", label="View Action Tracker")

    else:
        st.divider()
        st.success("No critical or high-priority gaps identified. Continue monitoring regulatory developments.")

finally:
    db.close()
