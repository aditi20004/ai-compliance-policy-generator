import anthropic

from app.config import settings
from app.rag_service import rag_service

SYSTEM_PROMPT = """You are an Australian AI compliance expert specialising in policy development for small and medium enterprises (SMEs).

Your role is to generate policy clauses that are:
- Grounded in the provided Australian regulatory text
- Tailored to the organisation's specific industry, size, and AI usage
- Citing specific principles, acts, or guidelines where applicable
- Written in clear, professional policy language suitable for an SME audience
- Practical and actionable rather than overly legalistic

Always reference specific Australian regulations:
- Privacy Act 1988 and Australian Privacy Principles (APPs)
- Australia's 8 AI Ethics Principles
- OAIC guidance on AI and privacy
- Notifiable Data Breaches (NDB) scheme where relevant

Format your output as policy-ready text with clear headings and bullet points."""


def _build_clause_prompt(template_type: str, questionnaire_data: dict, regulatory_context: str) -> str:
    template_descriptions = {
        "ai_acceptable_use": "AI Acceptable Use Policy — covering scope, approved/prohibited uses, data handling, human oversight, transparency, and review schedule",
        "data_classification": "Data Classification Policy for AI — covering classification tiers (public/internal/confidential/restricted) and rules per tier for AI input",
        "incident_response": "AI Incident Response Plan — covering detection, containment, notification (OAIC breach reporting), recovery, and lessons learned",
        "vendor_risk_assessment": "AI Vendor Risk Assessment Policy — covering vendor risk tiers, pre-onboarding assessment, DPA requirements, APP 8 cross-border obligations, and ongoing monitoring",
        "ai_ethics_framework": "AI Ethics & Fairness Framework — covering Australia's 8 AI Ethics Principles, bias testing, explainability, human oversight, and contestability mechanisms",
        "employee_ai_training": "Employee AI Training Guide — covering AI usage responsibilities, data handling rules, shadow AI risks, incident reporting, and privacy obligations",
        "ai_risk_register": "AI Risk Register — covering risk identification, likelihood/impact assessment, mitigation controls, risk owners, and review schedule",
        "privacy_policy": "APP-Compliant Privacy Policy — covering collection, use, disclosure, APP 8 cross-border, POLA Act automated decision disclosure, and data security",
        "board_ai_briefing": "Board AI Risk Briefing — covering regulatory landscape, penalty exposure, governance posture, strategic recommendations, and POLA Act timeline",
        "remediation_action_plan": "Remediation Action Plan — covering prioritised gap analysis, 30/60/90-day action items, resource requirements, and compliance milestones",
    }

    description = template_descriptions.get(template_type, template_type)

    # Sanitise user-supplied fields to mitigate prompt injection
    biz = _sanitise_field(questionnaire_data.get("business_name", "N/A"))
    industry = _sanitise_field(questionnaire_data.get("industry", "N/A"))
    tools = [_sanitise_field(t, 80) for t in questionnaire_data.get("ai_tools_in_use", [])]
    dtypes = [_sanitise_field(d, 80) for d in questionnaire_data.get("data_types_processed", [])]

    prompt = f"""Generate customised regulatory alignment notes for a {description}.

Organisation Details:
- Business Name: {biz}
- Industry: {industry}
- Employee Count: {questionnaire_data.get("employee_count", "N/A")}
- Revenue Exceeds $3M Threshold: {questionnaire_data.get("revenue_exceeds_threshold", False)}
- AI Tools in Use: {", ".join(tools)}
- Data Types Processed: {", ".join(dtypes)}
- Automated Decisions Affecting Individuals: {questionnaire_data.get("automated_decisions", False)}
- Existing IT Policies: {questionnaire_data.get("existing_it_policies", False)}
- Training Frequency: {questionnaire_data.get("training_frequency", "annually")}

Regulatory Context (use this to ground your response):
---
{regulatory_context}
---

Generate 3-5 regulatory alignment notes that:
1. Map the organisation's specific situation to relevant Australian regulations
2. Highlight key compliance obligations based on their industry and data types
3. Provide actionable recommendations tailored to their size and maturity
4. Cite specific APPs, AI Ethics Principles, or OAIC guidance"""

    return prompt


def _sanitise_field(value: str, max_length: int = 200) -> str:
    """Sanitise user-supplied text before including in LLM prompts."""
    if not isinstance(value, str):
        return str(value)
    # Truncate and strip control characters
    return value[:max_length].replace("\r", "").replace("\n", " ").replace("\x00", "")


_client: anthropic.Anthropic | None = None


def _get_client() -> anthropic.Anthropic:
    """Reuse a single Anthropic client for connection pooling."""
    global _client
    if _client is None:
        _client = anthropic.Anthropic(api_key=settings.anthropic_api_key)
    return _client


def generate_policy_clauses(template_type: str, questionnaire_data: dict) -> str:
    """Generate customised policy clauses using LLM API with RAG context."""
    if not settings.anthropic_api_key:
        return "(AI API key not configured — using template defaults)"

    # Get regulatory context from RAG
    regulatory_context = rag_service.get_context_for_template(template_type, questionnaire_data)

    prompt = _build_clause_prompt(template_type, questionnaire_data, regulatory_context)

    try:
        client = _get_client()
        message = client.messages.create(
            model="claude-sonnet-4-20250514",
            max_tokens=1500,
            system=SYSTEM_PROMPT,
            messages=[{"role": "user", "content": prompt}],
        )
        if not message.content:
            return "(AI returned empty response — using template defaults)"
        return message.content[0].text  # type: ignore[union-attr]
    except anthropic.AuthenticationError:
        return "(AI API key is invalid — using template defaults)"
    except (anthropic.RateLimitError, anthropic.APIConnectionError, anthropic.APITimeoutError) as exc:
        return f"(AI service temporarily unavailable: {type(exc).__name__} — using template defaults)"
    except Exception as exc:
        import logging

        logging.getLogger(__name__).error("Unexpected LLM error: %s", exc, exc_info=True)
        return f"(AI enhancement failed: {type(exc).__name__} — using template defaults)"
