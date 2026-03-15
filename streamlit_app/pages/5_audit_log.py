import sys
from html import escape
from pathlib import Path

import streamlit as st

sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent))

from components.sidebar import render_sidebar
from components.theme import status_badge

from app.audit import get_audit_logs
from app.database import SessionLocal, init_db

render_sidebar()
init_db()

st.title("Audit Log")

db = SessionLocal()
try:

    # Filters
    with st.container(border=True):
        col1, col2, col3 = st.columns(3)
        with col1:
            org_filter = st.number_input("Filter by Organisation ID", min_value=0, value=0, step=1)
        with col2:
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
        with col3:
            limit = st.number_input("Max Results", min_value=10, max_value=500, value=100, step=10)

    logs = get_audit_logs(
        db,
        org_id=org_filter if org_filter > 0 else None,
        event_type=event_filter if event_filter != "All" else None,
        limit=limit,
    )

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
