import sys
from html import escape
from pathlib import Path

import streamlit as st

sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent))

from components.sidebar import render_sidebar
from components.theme import status_badge

from app.database import SessionLocal, init_db

render_sidebar()
init_db()

st.title("Audit Log")

# Only show logs for organisations created in this session
session_org_ids = st.session_state.get("session_org_ids", set())
if not session_org_ids:
    st.info("Complete the questionnaire first to see audit logs.")
    st.stop()

db = SessionLocal()
try:

    # Filters
    with st.container(border=True):
        col1, col2, col3 = st.columns(3)
        with col1:
            event_filter = st.selectbox(
                "Filter by Event Type",
                options=[
                    "All",
                    "questionnaire_submitted",
                    "questionnaire_updated",
                    "policy_generated",
                    "policy_downloaded",
                    "compliance_snapshot",
                    "evidence_uploaded",
                    "evidence_removed",
                ],
            )
        with col2:
            limit = st.number_input("Max Results", min_value=10, max_value=500, value=100, step=10)

    # Fetch logs only for this session's organisations
    from app.models import AuditLog

    query = db.query(AuditLog).filter(AuditLog.org_id.in_(session_org_ids))
    if event_filter != "All":
        query = query.filter(AuditLog.event_type == event_filter)
    logs = query.order_by(AuditLog.timestamp.desc()).limit(limit).all()

    if not logs:
        st.info("No audit log entries found.")
    else:
        st.write(f"Showing {len(logs)} entries")

        _EVENT_BADGE_COLORS = {
            "questionnaire_submitted": "green",
            "questionnaire_updated": "green",
            "policy_generated": "blue",
            "policy_downloaded": "orange",
            "compliance_snapshot": "blue",
            "evidence_uploaded": "green",
            "evidence_removed": "orange",
        }

        for log in logs:
            with st.container(border=True):
                col1, col2, col3, col4 = st.columns([2, 1, 2, 2])
                with col1:
                    badge_color = _EVENT_BADGE_COLORS.get(log.event_type, "gray")
                    st.markdown(status_badge(log.event_type.replace("_", " ").title(), badge_color), unsafe_allow_html=True)
                with col2:
                    if log.org_id:
                        st.markdown(
                            f'<span class="audit-org">Org #{log.org_id}</span>',
                            unsafe_allow_html=True,
                        )
                with col3:
                    st.caption(log.timestamp.strftime("%Y-%m-%d %H:%M:%S") if log.timestamp else "")
                with col4:
                    if log.content_hash:
                        st.markdown(
                            f'<span style="font-family:monospace;font-size:0.8rem;color:#94a3b8;background:#f8fafc;padding:2px 8px;border-radius:4px;">{escape(log.content_hash[:16])}...</span>',
                            unsafe_allow_html=True,
                        )

                if log.metadata_json:
                    with st.expander("Details"):
                        st.json(log.metadata_json)

finally:
    db.close()
