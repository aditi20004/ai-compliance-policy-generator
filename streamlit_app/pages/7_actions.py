import datetime
import sys
from pathlib import Path

import streamlit as st

sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent))

from components.sidebar import render_sidebar

from app.database import SessionLocal, init_db
from app.models import Organisation, RemediationAction

render_sidebar()
init_db()

st.title("Remediation Action Tracker")

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

    st.write(f"Action tracker for **{org.business_name}**")

    # Load all actions for this org
    actions = (
        db.query(RemediationAction)
        .filter(RemediationAction.org_id == org_id)
        .order_by(RemediationAction.deadline.asc())
        .all()
    )

    if not actions:
        st.info("No remediation actions yet. Visit the Compliance Scorecard to generate actions from compliance gaps.")
        st.page_link("pages/4_compliance.py", label="Go to Compliance Scorecard")
        st.stop()

    # Mark overdue actions
    today = datetime.date.today()
    _overdue_updated = False
    for action in actions:
        if action.status in ("pending", "in_progress") and action.deadline.date() < today:
            action.status = "overdue"
            _overdue_updated = True
    if _overdue_updated:
        db.commit()

    # --- Summary Metrics ---
    total = len(actions)
    completed = sum(1 for a in actions if a.status == "completed")
    overdue = sum(1 for a in actions if a.status == "overdue")
    in_progress = sum(1 for a in actions if a.status == "in_progress")
    pending = sum(1 for a in actions if a.status == "pending")

    col1, col2, col3, col4, col5 = st.columns(5)
    with col1:
        st.metric("Total Actions", total)
    with col2:
        st.metric("Completed", completed, delta=f"{round(completed / total * 100)}%" if total else "0%")
    with col3:
        st.metric("In Progress", in_progress)
    with col4:
        st.metric("Pending", pending)
    with col5:
        if overdue > 0:
            st.metric("Overdue", overdue, delta="Action needed", delta_color="inverse")
        else:
            st.metric("Overdue", 0, delta="On track")

    # Progress bar
    if total > 0:
        progress = completed / total
        st.progress(progress, text=f"Overall completion: {round(progress * 100)}%")

    st.divider()

    # --- Filter ---
    filter_col1, filter_col2 = st.columns(2)
    with filter_col1:
        status_filter = st.multiselect(
            "Filter by status",
            options=["pending", "in_progress", "overdue", "completed"],
            default=["overdue", "pending", "in_progress"],
            key="action_status_filter",
        )
    with filter_col2:
        severity_filter = st.multiselect(
            "Filter by severity",
            options=["critical", "high", "medium", "low"],
            default=["critical", "high", "medium", "low"],
            key="action_severity_filter",
        )

    filtered_actions = [a for a in actions if a.status in status_filter and a.severity in severity_filter]

    # --- Timeline Buckets ---
    SEVERITY_CONFIG = {
        "critical": {"color": "red", "label": "Critical", "timeline": "30-Day"},
        "high": {"color": "orange", "label": "High", "timeline": "60-Day"},
        "medium": {"color": "blue", "label": "Medium", "timeline": "90-Day"},
        "low": {"color": "gray", "label": "Low", "timeline": "120-Day"},
    }

    STATUS_ICONS = {
        "pending": "[Pending]",
        "in_progress": "[In Progress]",
        "completed": "[Done]",
        "overdue": "[Overdue]",
    }

    _SEVERITY_BORDER_COLORS = {
        "critical": "#dc2626",
        "high": "#ea580c",
        "medium": "#2563eb",
        "low": "#64748b",
    }

    for severity in ["critical", "high", "medium", "low"]:
        sev_actions = [a for a in filtered_actions if a.severity == severity]
        if not sev_actions:
            continue

        config = SEVERITY_CONFIG[severity]
        sev_border = _SEVERITY_BORDER_COLORS[severity]
        st.markdown(
            f"""
        <div style="border-left:4px solid {sev_border}; padding:4px 0 4px 14px; margin:20px 0 10px 0;">
            <span style="font-weight:700; color:#1a3c6e; font-size:1.1rem;">{config["timeline"]} Actions</span>
            <span style="margin-left:8px;background:{sev_border}15;color:{sev_border};padding:2px 10px;border-radius:20px;font-size:0.75rem;font-weight:600;border:1px solid {sev_border}30;">{config["label"]}</span>
        </div>
        """,
            unsafe_allow_html=True,
        )

        for action in sev_actions:
            icon = STATUS_ICONS.get(action.status, "[Pending]")
            days_left = (action.deadline.date() - today).days

            # Deadline indicator
            if action.status == "completed":
                deadline_text = f"Completed {action.completed_at.strftime('%Y-%m-%d') if action.completed_at else ''}"
            elif days_left < 0:
                deadline_text = f":red[**{abs(days_left)} days overdue**]"
            elif days_left <= 7:
                deadline_text = f":orange[Due in {days_left} days]"
            else:
                deadline_text = f"Due: {action.deadline.strftime('%Y-%m-%d')} ({days_left} days)"

            _STATUS_BADGE_COLORS = {
                "pending": ("#64748b", "#f8fafc"),
                "in_progress": ("#2563eb", "#eff6ff"),
                "completed": ("#16a34a", "#f0fdf4"),
                "overdue": ("#dc2626", "#fef2f2"),
            }

            with st.container(border=True):
                header_col, status_col = st.columns([4, 1])

                with header_col:
                    st.markdown(f"{icon} **{action.checklist_item_name}**")
                    st.caption(f"{deadline_text}")

                with status_col:
                    _sfg, _sbg = _STATUS_BADGE_COLORS.get(action.status, ("#64748b", "#f8fafc"))
                    st.markdown(
                        f'<span style="background:{_sbg};color:{_sfg};padding:3px 10px;border-radius:20px;font-size:0.75rem;font-weight:600;border:1px solid {_sfg}20">{action.status.upper()}</span>',
                        unsafe_allow_html=True,
                    )

                st.write(action.action_description)

                # Action buttons row
                if action.status != "completed":
                    btn_col1, btn_col2, btn_col3 = st.columns([1, 1, 2])

                    with btn_col1:
                        if action.status in ("pending", "overdue"):
                            if st.button("Start", key=f"start_{action.id}", use_container_width=True):
                                action.status = "in_progress"
                                db.commit()
                                st.rerun()

                    with btn_col2:
                        if action.status in ("pending", "in_progress", "overdue"):
                            if st.button("Complete", key=f"complete_{action.id}", type="primary", use_container_width=True):
                                action.status = "completed"
                                action.completed_at = datetime.datetime.now(datetime.timezone.utc)
                                db.commit()
                                st.rerun()

                    with btn_col3:
                        notes = st.text_input(
                            "Notes",
                            value=action.notes or "",
                            key=f"notes_{action.id}",
                            label_visibility="collapsed",
                            placeholder="Add notes...",
                        )
                        if notes != (action.notes or ""):
                            if st.button("Save", key=f"save_notes_{action.id}"):
                                action.notes = notes
                                db.commit()
                                st.rerun()
                else:
                    if action.notes:
                        st.caption(f"Notes: {action.notes}")
                    if action.completed_at:
                        st.caption(f"Completed: {action.completed_at.strftime('%Y-%m-%d %H:%M')}")

    # --- Completed Actions (collapsed) ---
    completed_actions = [a for a in actions if a.status == "completed"]
    if completed_actions:
        st.divider()
        with st.expander(f"Completed Actions ({len(completed_actions)})", expanded=False):
            for action in completed_actions:
                st.markdown(f"[Done] ~~{action.checklist_item_name}~~")
                st.caption(
                    f"Severity: {action.severity} | "
                    f"Completed: {action.completed_at.strftime('%Y-%m-%d') if action.completed_at else 'N/A'}"
                    + (f" | Notes: {action.notes}" if action.notes else "")
                )

    st.divider()
    st.page_link("pages/4_compliance.py", label="Back to Compliance Scorecard")

finally:
    db.close()
