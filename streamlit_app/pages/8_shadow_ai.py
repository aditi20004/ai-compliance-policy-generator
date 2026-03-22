import csv
import datetime
import io
import re
import sys
from collections import Counter
from pathlib import Path

import streamlit as st

sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent))

from components.sidebar import render_sidebar

from app.audit import log_event
from app.database import SessionLocal, init_db
from app.models import Organisation

render_sidebar()
init_db()


def _is_approved(service_name: str, approved_tools: list[str]) -> bool:
    """Bidirectional substring match between AI service name and approved tool names."""
    svc = service_name.lower()
    return any(svc in tool.lower() or tool.lower() in svc for tool in approved_tools)


st.title("Shadow AI Blocklist & Governance")

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
        st.error("Organisation not found.")
        st.stop()

    st.write(f"Shadow AI governance tools for **{org.business_name}**")

    # --- Known AI Service Domains ---
    AI_DOMAINS = {
        # Large language models & chatbots
        "chat.openai.com": {"service": "ChatGPT", "vendor": "OpenAI", "category": "LLM Chatbot", "risk": "high"},
        "chatgpt.com": {"service": "ChatGPT", "vendor": "OpenAI", "category": "LLM Chatbot", "risk": "high"},
        "api.openai.com": {"service": "OpenAI API", "vendor": "OpenAI", "category": "LLM API", "risk": "high"},
        "platform.openai.com": {"service": "OpenAI Platform", "vendor": "OpenAI", "category": "LLM API", "risk": "high"},
        "claude.ai": {"service": "Claude", "vendor": "Anthropic", "category": "LLM Chatbot", "risk": "high"},
        "api.anthropic.com": {"service": "Anthropic API", "vendor": "Anthropic", "category": "LLM API", "risk": "high"},
        "gemini.google.com": {"service": "Gemini", "vendor": "Google", "category": "LLM Chatbot", "risk": "high"},
        "generativelanguage.googleapis.com": {
            "service": "Gemini API",
            "vendor": "Google",
            "category": "LLM API",
            "risk": "high",
        },
        "bard.google.com": {"service": "Bard (legacy)", "vendor": "Google", "category": "LLM Chatbot", "risk": "high"},
        "copilot.microsoft.com": {"service": "Copilot", "vendor": "Microsoft", "category": "LLM Chatbot", "risk": "high"},
        "bing.com/chat": {"service": "Bing Chat", "vendor": "Microsoft", "category": "LLM Chatbot", "risk": "medium"},
        "grok.x.ai": {"service": "Grok", "vendor": "xAI", "category": "LLM Chatbot", "risk": "high"},
        "perplexity.ai": {"service": "Perplexity", "vendor": "Perplexity AI", "category": "AI Search", "risk": "medium"},
        "poe.com": {"service": "Poe", "vendor": "Quora", "category": "LLM Aggregator", "risk": "high"},
        "character.ai": {"service": "Character.AI", "vendor": "Character.AI", "category": "LLM Chatbot", "risk": "medium"},
        "you.com": {"service": "You.com", "vendor": "You.com", "category": "AI Search", "risk": "medium"},
        "huggingface.co": {
            "service": "Hugging Face",
            "vendor": "Hugging Face",
            "category": "ML Platform",
            "risk": "medium",
        },
        "replicate.com": {"service": "Replicate", "vendor": "Replicate", "category": "ML Platform", "risk": "medium"},
        "together.ai": {"service": "Together AI", "vendor": "Together", "category": "LLM API", "risk": "medium"},
        "groq.com": {"service": "Groq", "vendor": "Groq", "category": "LLM API", "risk": "medium"},
        "mistral.ai": {"service": "Mistral", "vendor": "Mistral AI", "category": "LLM API", "risk": "high"},
        "cohere.com": {"service": "Cohere", "vendor": "Cohere", "category": "LLM API", "risk": "medium"},
        "deepseek.com": {"service": "DeepSeek", "vendor": "DeepSeek", "category": "LLM Chatbot", "risk": "high"},
        # Image generation
        "midjourney.com": {
            "service": "Midjourney",
            "vendor": "Midjourney",
            "category": "Image Generation",
            "risk": "medium",
        },
        "stability.ai": {
            "service": "Stable Diffusion",
            "vendor": "Stability AI",
            "category": "Image Generation",
            "risk": "medium",
        },
        "labs.openai.com": {"service": "DALL-E", "vendor": "OpenAI", "category": "Image Generation", "risk": "medium"},
        "leonardo.ai": {"service": "Leonardo AI", "vendor": "Leonardo", "category": "Image Generation", "risk": "medium"},
        "ideogram.ai": {"service": "Ideogram", "vendor": "Ideogram", "category": "Image Generation", "risk": "medium"},
        # Code assistants
        "github.com/features/copilot": {
            "service": "GitHub Copilot",
            "vendor": "Microsoft/GitHub",
            "category": "Code AI",
            "risk": "high",
        },
        "copilot.github.com": {
            "service": "GitHub Copilot",
            "vendor": "Microsoft/GitHub",
            "category": "Code AI",
            "risk": "high",
        },
        "cursor.sh": {"service": "Cursor", "vendor": "Cursor", "category": "Code AI", "risk": "high"},
        "replit.com": {"service": "Replit AI", "vendor": "Replit", "category": "Code AI", "risk": "medium"},
        "codeium.com": {"service": "Codeium", "vendor": "Codeium", "category": "Code AI", "risk": "medium"},
        "tabnine.com": {"service": "Tabnine", "vendor": "Tabnine", "category": "Code AI", "risk": "medium"},
        # Writing & productivity
        "jasper.ai": {"service": "Jasper", "vendor": "Jasper", "category": "AI Writing", "risk": "medium"},
        "grammarly.com": {"service": "Grammarly", "vendor": "Grammarly", "category": "AI Writing", "risk": "low"},
        "writesonic.com": {"service": "Writesonic", "vendor": "Writesonic", "category": "AI Writing", "risk": "medium"},
        "copy.ai": {"service": "Copy.ai", "vendor": "Copy.ai", "category": "AI Writing", "risk": "medium"},
        "notion.so/product/ai": {
            "service": "Notion AI",
            "vendor": "Notion",
            "category": "AI Productivity",
            "risk": "medium",
        },
        "otter.ai": {"service": "Otter.ai", "vendor": "Otter", "category": "AI Transcription", "risk": "high"},
        "fireflies.ai": {"service": "Fireflies.ai", "vendor": "Fireflies", "category": "AI Transcription", "risk": "high"},
        "descript.com": {"service": "Descript", "vendor": "Descript", "category": "AI Audio/Video", "risk": "medium"},
        "synthesia.io": {"service": "Synthesia", "vendor": "Synthesia", "category": "AI Video", "risk": "medium"},
        "elevenlabs.io": {"service": "ElevenLabs", "vendor": "ElevenLabs", "category": "AI Audio", "risk": "medium"},
        # Data & analytics
        "julius.ai": {"service": "Julius AI", "vendor": "Julius", "category": "AI Data Analysis", "risk": "high"},
        "datarobot.com": {"service": "DataRobot", "vendor": "DataRobot", "category": "AutoML", "risk": "high"},
        "obviously.ai": {"service": "Obviously AI", "vendor": "Obviously", "category": "AutoML", "risk": "medium"},
    }

    # --- Tab layout ---
    tab_blocklist, tab_analyse, tab_approved = st.tabs(["DNS Blocklist Export", "Log Analysis", "Approved vs Detected"])

    # ============================
    # TAB 1: DNS Blocklist Export
    # ============================
    with tab_blocklist:
        st.subheader("Generate DNS Blocklist")
        st.write(
            "Export a blocklist of known AI service domains for your network security tools. "
            "This helps prevent unauthorised AI tool usage on corporate networks."
        )

        # Let user select which categories to block
        all_categories = sorted(set(d["category"] for d in AI_DOMAINS.values()))
        selected_categories = st.multiselect(
            "Select AI categories to block",
            options=all_categories,
            default=[c for c in all_categories if c != "AI Writing"],  # Don't block Grammarly by default
            key="blocklist_categories",
        )

        # Filter domains by selected categories
        blocked_domains = {domain: info for domain, info in AI_DOMAINS.items() if info["category"] in selected_categories}

        # Allow user to exclude approved tools
        approved_tools = org.ai_tools_in_use or []
        if approved_tools:
            st.info(f"Your approved AI tools ({len(approved_tools)}): {', '.join(approved_tools)}")
            exclude_approved = st.checkbox("Exclude approved tools from blocklist", value=True, key="exclude_approved")
            if exclude_approved:
                blocked_domains = {
                    domain: info
                    for domain, info in blocked_domains.items()
                    if not _is_approved(info["service"], approved_tools)
                }

        st.write(f"**{len(blocked_domains)} domains** will be included in the blocklist.")

        # Preview
        with st.expander("Preview blocked domains"):
            for domain, info in sorted(blocked_domains.items()):
                risk_color = {"high": "red", "medium": "orange", "low": "green"}.get(info["risk"], "gray")
                st.markdown(f"- `{domain}` — {info['service']} (:{risk_color}[{info['risk']}])")

        # Export formats
        st.write("**Export Format:**")
        fmt = st.radio(
            "Choose format",
            options=["Pi-hole", "pfSense / Unbound", "Windows Defender / hosts file", "Plain list"],
            key="blocklist_format",
            label_visibility="collapsed",
        )

        domain_list = sorted(blocked_domains.keys())

        if fmt == "Pi-hole":
            content = "\n".join(domain_list)
            filename = "ai_blocklist_pihole.txt"
            st.caption("Format: one domain per line (Pi-hole gravity list)")
        elif fmt == "pfSense / Unbound":
            content = "\n".join(f'local-zone: "{d}" always_nxdomain' for d in domain_list)
            filename = "ai_blocklist_unbound.conf"
            st.caption("Format: Unbound local-zone NXDOMAIN entries")
        elif fmt == "Windows Defender / hosts file":
            content = "\n".join(f"0.0.0.0 {d}" for d in domain_list)
            filename = "ai_blocklist_hosts.txt"
            st.caption("Format: hosts file redirect to 0.0.0.0")
        else:
            content = "\n".join(domain_list)
            filename = "ai_blocklist.txt"
            st.caption("Format: plain domain list")

        downloaded = st.download_button(
            label=f"Download Blocklist ({len(domain_list)} domains)",
            data=content,
            file_name=filename,
            mime="text/plain",
            type="primary",
            use_container_width=True,
        )

        if downloaded:
            log_event(
                db, event_type="blocklist_exported", org_id=org_id, metadata={"format": fmt, "domain_count": len(domain_list)}
            )

    # ============================
    # TAB 2: Log Analysis
    # ============================
    with tab_analyse:
        st.subheader("DNS / Proxy Log Analysis")
        st.write("Upload your DNS query logs or web proxy logs to detect AI service usage on your network.")

        st.info(
            "**Supported formats:** CSV, TSV, or plain text with one domain/URL per line. "
            "Common formats from Pi-hole, pfSense, Squid proxy, and Windows DNS logs are supported."
        )

        uploaded_log = st.file_uploader(
            "Upload log file",
            type=["csv", "tsv", "txt", "log"],
            key="log_upload",
        )

        if uploaded_log:
            raw = uploaded_log.getvalue().decode("utf-8", errors="replace")
            lines = raw.strip().split("\n")

            # Extract domains from various log formats
            detected_domains = []
            domain_pattern = re.compile(r"(?:https?://)?([a-zA-Z0-9][-a-zA-Z0-9]*(?:\.[a-zA-Z0-9][-a-zA-Z0-9]*)+)")

            for line in lines:
                matches = domain_pattern.findall(line)
                for match in matches:
                    # Clean up domain
                    domain = match.lower().strip(".")
                    detected_domains.append(domain)

            # Match against known AI domains
            ai_hits = Counter()
            ai_detail_hits = {}

            for domain in detected_domains:
                for ai_domain, info in AI_DOMAINS.items():
                    # Check exact match or subdomain match
                    if domain == ai_domain or domain.endswith("." + ai_domain):
                        ai_hits[ai_domain] += 1
                        ai_detail_hits[ai_domain] = info

            st.divider()

            if ai_hits:
                st.error(f"**{len(ai_hits)} AI services detected** across {sum(ai_hits.values())} requests")

                # Deduplicate audit log: only log once per uploaded file
                _scan_log_key = f"_shadow_scan_logged_{uploaded_log.name}_{len(ai_hits)}"
                if not st.session_state.get(_scan_log_key):
                    log_event(
                        db,
                        event_type="shadow_ai_scan",
                        org_id=org_id,
                        metadata={
                            "file": uploaded_log.name,
                            "ai_services_found": len(ai_hits),
                            "total_requests": sum(ai_hits.values()),
                        },
                    )
                    st.session_state[_scan_log_key] = True

                # Risk summary
                risk_counts = Counter()
                for domain, info in ai_detail_hits.items():
                    risk_counts[info["risk"]] += ai_hits[domain]

                rc1, rc2, rc3 = st.columns(3)
                with rc1:
                    st.metric("High Risk Requests", risk_counts.get("high", 0))
                with rc2:
                    st.metric("Medium Risk Requests", risk_counts.get("medium", 0))
                with rc3:
                    st.metric("Low Risk Requests", risk_counts.get("low", 0))

                st.divider()

                # Detailed breakdown
                st.write("**Detected AI Services:**")
                for domain in sorted(ai_hits.keys(), key=lambda d: ai_hits[d], reverse=True):
                    info = ai_detail_hits[domain]
                    count = ai_hits[domain]
                    risk_color = {"high": "red", "medium": "orange", "low": "green"}.get(info["risk"], "gray")

                    # Check if this is an approved tool
                    is_tool_approved = _is_approved(info["service"], org.ai_tools_in_use or [])
                    approved_badge = " :green[(Approved)]" if is_tool_approved else " :red[(Unapproved)]"

                    with st.container(border=True):
                        col1, col2, col3 = st.columns([3, 1, 1])
                        with col1:
                            st.markdown(f"**{info['service']}**{approved_badge}")
                            st.caption(f"Vendor: {info['vendor']} | Category: {info['category']}")
                        with col2:
                            st.metric("Requests", count)
                        with col3:
                            st.markdown(f":{risk_color}[**{info['risk'].upper()}**]")

                # Export findings as CSV
                csv_buffer = io.StringIO()
                writer = csv.writer(csv_buffer)
                writer.writerow(["Domain", "Service", "Vendor", "Category", "Risk", "Requests", "Approved"])
                for domain in sorted(ai_hits.keys(), key=lambda d: ai_hits[d], reverse=True):
                    info = ai_detail_hits[domain]
                    is_tool_approved = _is_approved(info["service"], org.ai_tools_in_use or [])
                    writer.writerow(
                        [
                            domain,
                            info["service"],
                            info["vendor"],
                            info["category"],
                            info["risk"],
                            ai_hits[domain],
                            "Yes" if is_tool_approved else "No",
                        ]
                    )

                st.download_button(
                    label="Export Findings as CSV",
                    data=csv_buffer.getvalue(),
                    file_name=f"shadow_ai_findings_{''.join(c if c.isalnum() or c in '-_ ' else '' for c in org.business_name)[:80]}_{datetime.date.today()}.csv",
                    mime="text/csv",
                    use_container_width=True,
                )
            else:
                st.success("No known AI service domains detected in the uploaded log.")
                st.caption(f"Scanned {len(set(detected_domains))} unique domains against {len(AI_DOMAINS)} known AI services.")

    # ============================
    # TAB 3: Approved vs Detected
    # ============================
    with tab_approved:
        st.subheader("AI Tool Inventory")
        st.write("Compare your declared AI tools against the known AI service database.")

        declared_tools = org.ai_tools_in_use or []
        overseas_tools = org.ai_tools_overseas or []

        col_dec, col_db = st.columns(2)

        with col_dec:
            st.write("**Declared AI Tools (from questionnaire):**")
            if declared_tools:
                for tool in declared_tools:
                    # Check if it's in our database (fuzzy match)
                    matched = False
                    for domain, info in AI_DOMAINS.items():
                        if _is_approved(info["service"], [tool]):
                            risk_color = {"high": "red", "medium": "orange", "low": "green"}.get(info["risk"], "gray")
                            overseas_flag = " :orange[(Overseas)]" if tool in overseas_tools else ""
                            st.markdown(f"- **{tool}** — {info['vendor']} :{risk_color}[{info['risk']}]{overseas_flag}")
                            matched = True
                            break
                    if not matched:
                        st.markdown(f"- **{tool}** — :gray[Not in database]")
            else:
                st.info("No AI tools declared. Update the questionnaire if your organisation uses AI tools.")

        with col_db:
            st.write("**Common AI Services (not declared):**")
            # Show popular services NOT in the declared list
            popular = [
                "ChatGPT",
                "Claude",
                "Gemini",
                "Copilot",
                "Midjourney",
                "Grammarly",
                "GitHub Copilot",
                "Perplexity",
                "Otter.ai",
                "DeepSeek",
            ]
            undeclared = [s for s in popular if not _is_approved(s, declared_tools)]
            if undeclared:
                st.caption(
                    "These popular AI services are not in your declared tool list. "
                    "Consider surveying staff to check if any are in use."
                )
                for service in undeclared:
                    st.write(f"- {service}")
            else:
                st.success("All common AI services are accounted for in your declarations.")

        st.divider()

        # Shadow AI awareness status
        st.write("**Shadow AI Governance Status:**")

        checks = [
            ("Shadow AI awareness", org.shadow_ai_aware, "Organisation is aware of shadow AI risks"),
            ("Shadow AI controls", org.shadow_ai_controls, "Technical controls are in place to prevent unapproved AI use"),
            (
                "AI content review",
                org.ai_generated_content_reviewed,
                "AI-generated content is reviewed before external use",
            ),
            ("Vendor DPA in place", org.vendor_dpa_in_place, "Data Processing Agreements exist with AI vendors"),
        ]

        for label, value, desc in checks:
            if value:
                st.markdown(f":white_check_mark: **{label}** — {desc}")
            else:
                st.markdown(f":x: **{label}** — {desc}")

        shadow_score = sum(1 for _, v, _ in checks if v)
        if shadow_score == len(checks):
            st.success("Shadow AI governance is well-established.")
        elif shadow_score >= 2:
            st.warning(f"Shadow AI governance: {shadow_score}/{len(checks)} controls in place. Improvement needed.")
        else:
            st.error(f"Shadow AI governance: {shadow_score}/{len(checks)} controls. Significant risk exposure.")

finally:
    db.close()
