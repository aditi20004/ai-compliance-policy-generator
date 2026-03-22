import os
from html import escape

import streamlit as st

from components.theme import apply_theme


def render_sidebar():
    apply_theme()

    with st.sidebar:
        st.markdown(
            """
        <div style="text-align:center; padding: 10px 0 5px 0;">
            <div style="font-size:1.4rem; font-weight:800; color:#ffffff;">AI-CPG</div>
            <div style="font-size:1.1rem; font-weight:800; letter-spacing:-0.02em; color:#ffffff !important;">
                AI Compliance<br>Policy Generator
            </div>
            <div style="font-size:0.75rem; color:#94a3b8 !important; margin-top:2px;">
                For Australian SMEs
            </div>
        </div>
        """,
            unsafe_allow_html=True,
        )

        st.divider()

        # --- Multi-Org Switcher ---
        _render_org_switcher()

        st.divider()

        # Logo upload
        st.markdown(
            """
        <div style="font-size:0.7rem; text-transform:uppercase; letter-spacing:0.08em; color:#94a3b8 !important; margin-bottom:6px;">Company Logo</div>
        """,
            unsafe_allow_html=True,
        )
        uploaded_logo = st.file_uploader(
            "Upload logo for PDFs", type=["png", "jpg", "jpeg"], key="logo_upload", label_visibility="collapsed"
        )
        if uploaded_logo:
            _MAX_LOGO_MB = 2
            if len(uploaded_logo.getbuffer()) > _MAX_LOGO_MB * 1024 * 1024:
                st.error(f"Logo too large. Maximum size is {_MAX_LOGO_MB} MB.")
            else:
                logo_dir = os.path.join(
                    os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))), "assets"
                )
                os.makedirs(logo_dir, exist_ok=True)
                # Include org_id in filename to avoid cross-org overwrites
                _org_suffix = st.session_state.get("org_id", "default")
                logo_path = os.path.join(logo_dir, f"company_logo_{_org_suffix}.png")
                # Only write to disk if not already saved for this upload
                _logo_dedup_key = f"_logo_saved_{_org_suffix}_{uploaded_logo.name}_{len(uploaded_logo.getbuffer())}"
                if not st.session_state.get(_logo_dedup_key):
                    with open(logo_path, "wb") as f:
                        f.write(uploaded_logo.getbuffer())
                    st.session_state[_logo_dedup_key] = True
                st.session_state["logo_path"] = logo_path
                st.image(uploaded_logo, width=120)
        elif "logo_path" not in st.session_state:
            _org_suffix = st.session_state.get("org_id", "default")
            _base_dir = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
            # Try org-specific logo first, then generic fallback
            for _logo_name in (f"company_logo_{_org_suffix}.png", "company_logo.png"):
                default_logo = os.path.join(_base_dir, "assets", _logo_name)
                if os.path.exists(default_logo):
                    st.session_state["logo_path"] = default_logo
                    st.image(default_logo, width=120)
                    break

        st.divider()

        st.markdown(
            """
        <div style="font-size:0.7rem; text-transform:uppercase; letter-spacing:0.08em; color:#94a3b8 !important; margin-bottom:6px;">Regulatory Alignment</div>
        """,
            unsafe_allow_html=True,
        )

        regulations = [
            ("Privacy Act 1988", "Cth"),
            ("AI Ethics Principles", "8 Principles"),
            ("OAIC AI Guidance", "Oct 2024"),
            ("POLA Act 2024", "Dec 2026"),
            ("AI6 Practices", "6 Essential"),
            ("Australian Consumer Law", "ACL"),
        ]
        for name, detail in regulations:
            st.markdown(
                f"""
            <div style="font-size:0.8rem; padding:2px 0; color:#cbd5e1 !important;">
                - <strong>{name}</strong> <span style="color:#64748b !important;">({detail})</span>
            </div>
            """,
                unsafe_allow_html=True,
            )


def _render_org_switcher():
    """Render the organisation switcher in the sidebar."""
    from app.database import SessionLocal
    from app.models import Organisation

    # Only show organisations created in this session
    session_org_ids = st.session_state.get("session_org_ids", set())
    if not session_org_ids:
        st.info("Complete the questionnaire to get started.")
        return

    db = SessionLocal()
    try:
        orgs = (
            db.query(Organisation)
            .filter(Organisation.id.in_(session_org_ids))
            .order_by(Organisation.created_at.desc())
            .all()
        )
    finally:
        db.close()

    if not orgs:
        st.info("Complete the questionnaire to get started.")
        return

    # Build options: list of (id, name) tuples
    org_options = {org.id: f"{org.business_name} (ID: {org.id})" for org in orgs}
    current_org_id = st.session_state.get("org_id")

    # If current org_id is not in the list, default to the first one
    if current_org_id not in org_options:
        current_org_id = orgs[0].id

    st.markdown(
        """
    <div style="font-size:0.7rem; text-transform:uppercase; letter-spacing:0.08em; color:#94a3b8 !important; margin-bottom:6px;">Organisation</div>
    """,
        unsafe_allow_html=True,
    )

    selected_id = st.selectbox(
        "Switch organisation",
        options=list(org_options.keys()),
        index=list(org_options.keys()).index(current_org_id) if current_org_id in org_options else 0,
        format_func=lambda x: org_options[x],
        key="org_switcher",
        label_visibility="collapsed",
    )

    # Update session state when org changes
    if selected_id != st.session_state.get("org_id"):
        st.session_state.org_id = selected_id
        # Look up the business name
        for org in orgs:
            if org.id == selected_id:
                st.session_state.business_name = org.business_name
                break
        # Clear snapshot cache, questionnaire state, and org-specific artifacts
        for key in list(st.session_state.keys()):
            if key.startswith(("snapshot_saved_", "_compliance_report", "_remediation", "_ev_saved_", "_logo_saved_")):
                del st.session_state[key]
        for key in ["q_step", "q_answers", "q_session_key", "q_edit_org_id", "preselect_templates"]:
            st.session_state.pop(key, None)
        st.cache_data.clear()

    # Show current org info card
    st.markdown(
        f"""
    <div style="background:rgba(255,255,255,0.08); border-radius:8px; padding:10px 12px; margin-top:6px; margin-bottom:4px;">
        <div style="font-size:0.95rem; font-weight:600; color:#ffffff !important;">{escape(str(st.session_state.get("business_name", "N/A")))}</div>
        <div style="font-size:0.75rem; color:#94a3b8 !important;">ID: {st.session_state.get("org_id", "N/A")}</div>
    </div>
    """,
        unsafe_allow_html=True,
    )

    if len(orgs) > 1:
        st.page_link("pages/6_compare.py", label="Compare Organisations")

    # Button to add another org
    if st.button("+ Add New Organisation", use_container_width=True, key="add_new_org"):
        st.session_state.q_step = 1
        st.session_state.q_answers = {}
        st.session_state.q_session_key = __import__("uuid").uuid4().hex
        # Don't clear org_id — the new one will be set on submission
        st.switch_page("pages/1_questionnaire.py")
