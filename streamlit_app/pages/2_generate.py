import sys
from pathlib import Path

import streamlit as st

sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent))

from components.sidebar import render_sidebar

from app.audit import log_event
from app.database import SessionLocal, init_db
from app.generator import (
    TEMPLATE_CATEGORIES,
    TEMPLATE_LABELS,
    generate_policy,
    recommend_templates,
)
from app.models import Organisation, PolicyDocument, org_to_dict

render_sidebar()
init_db()

st.title("Generate Policy Documents")

if "org_id" not in st.session_state or not st.session_state.get("org_id"):
    st.warning("Please complete the questionnaire first.")
    st.stop()

# Verify org belongs to this session
if st.session_state.org_id not in st.session_state.get("session_org_ids", set()):
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

    questionnaire_data = org_to_dict(org)
    recs = recommend_templates(questionnaire_data)
    recommended = recs["recommended"]
    optional = recs["optional"]

    # Accept pre-selection from Compliance page "Fix this" buttons
    _preselect = st.session_state.get("preselect_templates")
    st.session_state.pop("preselect_templates", None)

    # --- Policy Selection UI ---
    st.markdown("### Select policies to generate")
    st.caption(
        "Policies are recommended based on your questionnaire responses. "
        "Deselect any you don't need, or expand **Additional policies** to add more."
    )

    # Quick action buttons
    sel_col1, sel_col2 = st.columns(2)
    with sel_col1:
        if st.button("Select all recommended", use_container_width=True, key="sel_recommended"):
            st.session_state["_gen_selected"] = list(recommended)
            st.rerun()
    with sel_col2:
        if st.button("Select all", use_container_width=True, key="sel_all"):
            st.session_state["_gen_selected"] = list(recommended) + list(optional)
            st.rerun()

    # Determine default selection
    if _preselect:
        default_selection = _preselect
    elif "_gen_selected" in st.session_state:
        default_selection = st.session_state["_gen_selected"]
    else:
        default_selection = list(recommended)

    # Build category-grouped display
    selected_templates = []

    for category, cat_templates in TEMPLATE_CATEGORIES.items():
        cat_recommended = [t for t in cat_templates if t in recommended]
        cat_optional = [t for t in cat_templates if t in optional]

        if not cat_recommended and not cat_optional:
            continue

        with st.expander(f"**{category}** ({len(cat_recommended)} recommended, {len(cat_optional)} optional)", expanded=bool(cat_recommended)):
            for t in cat_recommended:
                label = TEMPLATE_LABELS.get(t, t)
                checked = st.checkbox(
                    f"{label}",
                    value=t in default_selection,
                    key=f"gen_{t}",
                    help="Recommended based on your profile",
                )
                if checked:
                    selected_templates.append(t)

            if cat_optional:
                for t in cat_optional:
                    label = TEMPLATE_LABELS.get(t, t)
                    checked = st.checkbox(
                        f"{label}",
                        value=t in default_selection,
                        key=f"gen_{t}",
                    )
                    if checked:
                        selected_templates.append(t)

    st.divider()

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

    st.markdown(f"**{len(selected_templates)}** policies selected")

    if st.button("Generate Policies", type="primary", use_container_width=True):
        if not selected_templates:
            st.warning("Please select at least one policy.")
        else:
            for template_type in selected_templates:
                try:
                    with st.spinner(f"Generating {TEMPLATE_LABELS.get(template_type, template_type)}..."):
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
                                <span style="font-weight:600;color:#1a3c6e;">{TEMPLATE_LABELS.get(template_type, template_type)}</span>
                                <span class="version-badge" style="background:#f0fdf4;color:#16a34a;border-color:#16a34a20;">v{policy.version}</span>
                                <span style="color:#64748b;font-size:0.8rem;">{output_format.upper()}</span>
                            </div>
                        </div>
                        """,
                            unsafe_allow_html=True,
                        )
                except Exception as e:
                    db.rollback()
                    st.error(f"Failed to generate {TEMPLATE_LABELS.get(template_type, template_type)}: {e}")

            st.info("Navigate to the **Policies** page to download your documents.")

finally:
    db.close()
