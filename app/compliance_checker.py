"""
Weighted compliance scorecard mapped to AI6 essential practices (24 items),
Australian regulatory requirements, and quantified penalty exposure.
"""

from sqlalchemy.orm import Session

# Regulatory penalty reference values (AUD) — from Privacy Act 1988, POLA Act 2024, ACL
PENALTIES = {
    "tier_1_admin": 330_000,          # 1,000 penalty units (s 13G, Privacy Act)
    "tier_2_interference": 3_300_000, # 10,000 penalty units (s 13G, Privacy Act)
    "tier_3_serious": 50_000_000,     # Greater of $50M / 30% turnover / 3x benefit (s 13G)
    "acl_max": 50_000_000,            # ACL s 224, body corporate
}

# Estimated business costs (AUD) — NOT regulatory fines
ESTIMATED_COSTS = {
    # POLA Act 2024 statutory tort — court-determined compensatory + aggravated damages.
    # No fixed cap. Estimate based on comparable Australian privacy tort settlements
    # and the ALRC's 2014 recommended cap of $478,550 (adjusted).
    # Source: ALRC Report 123, POLA Act 2024 Explanatory Memorandum
    "statutory_tort": 250_000,
    # Shadow AI breach cost — IBM 2025 Cost of a Data Breach Report found shadow AI
    # breaches cost USD $670K more than average. Scaled for Australian SMEs (<200 employees)
    # using OAIC SME breach cost ratio (~47% of enterprise average).
    # Source: IBM 2025 Cost of a Data Breach, OAIC NDB Report H1 2025
    "shadow_ai_sme": 350_000,
}


def _estimate_max_penalty_exposure(org_data: dict) -> dict:
    """Estimate maximum regulatory penalty exposure based on org profile."""
    regulatory_items = {}
    estimated_items = {}
    reg_total = 0
    est_total = 0

    # Privacy Act — depends on coverage (revenue > $3M, trades in PI, or health service provider)
    has_health_data = "Health Information" in (org_data.get("data_types_processed") or [])
    is_covered = (
        org_data.get("revenue_exceeds_threshold", False)
        or org_data.get("trades_in_personal_info", False)
        or has_health_data
    )

    if is_covered:
        # If they have automated decisions without disclosure = Tier 1
        if org_data.get("automated_decisions") and not org_data.get("pia_conducted"):
            regulatory_items["POLA Act non-compliance (Tier 1)"] = PENALTIES["tier_1_admin"]
            reg_total += PENALTIES["tier_1_admin"]

        # If handling sensitive data without proper controls = Tier 2
        sensitive_types = {
            "Health Information",
            "Biometric Data",
            "Financial Data (transactions, account numbers)",
            "Children's Data (under 18)",
            "AI-Inferred Data (profiles, predictions)",
        }
        has_sensitive = bool(sensitive_types & set(org_data.get("data_types_processed", [])))
        has_controls = org_data.get("ai_access_restricted", False) and org_data.get("pia_conducted", False)
        if has_sensitive and not has_controls:
            regulatory_items["Privacy Act interference (Tier 2)"] = PENALTIES["tier_2_interference"]
            reg_total += PENALTIES["tier_2_interference"]

        # Cross-border without DPA = Tier 2
        overseas = org_data.get("ai_tools_overseas", [])
        has_overseas = any(o for o in overseas if o != "None — all data stays in Australia")
        if has_overseas and not org_data.get("vendor_dpa_in_place"):
            regulatory_items["APP 8 cross-border non-compliance (Tier 2)"] = PENALTIES["tier_2_interference"]
            reg_total += PENALTIES["tier_2_interference"]

        # No privacy policy = Tier 1 (APP 1 breach)
        if not org_data.get("has_privacy_policy"):
            regulatory_items["APP 1 no privacy policy (Tier 1)"] = PENALTIES["tier_1_admin"]
            reg_total += PENALTIES["tier_1_admin"]
    else:
        regulatory_items["Note"] = (
            "Small business exemption currently applies, but removal is expected. Statutory tort still applies."  # type: ignore[assignment]
        )

    # ACL — customer-facing AI
    if org_data.get("customer_facing_ai") and not org_data.get("ai_generated_content_reviewed"):
        regulatory_items["ACL misleading conduct risk"] = PENALTIES["acl_max"]
        reg_total += PENALTIES["acl_max"]

    # Statutory tort — applies to ALL organisations (court-determined, not a fixed penalty)
    estimated_items["Statutory tort — estimated damages (any organisation)"] = ESTIMATED_COSTS["statutory_tort"]
    est_total += ESTIMATED_COSTS["statutory_tort"]

    # Shadow AI breach cost — applies if no controls regardless of awareness
    if not org_data.get("shadow_ai_controls"):
        employee_count = org_data.get("employee_count", 10)
        shadow_cost = min(int(ESTIMATED_COSTS["shadow_ai_sme"] * max(employee_count / 200, 0.5)), 2_000_000)
        estimated_items["Shadow AI data breach cost — estimated (IBM 2025)"] = shadow_cost
        est_total += shadow_cost

    # NDB scheme — failure to notify breach involving AI systems
    if is_covered and not org_data.get("ndb_ai_process"):
        regulatory_items["NDB scheme non-compliance (failure to notify)"] = PENALTIES["tier_2_interference"]
        reg_total += PENALTIES["tier_2_interference"]

    # Penalty stacking analysis — real enforcement can stack across multiple contraventions
    stacked_contraventions = len([v for k, v in regulatory_items.items() if k != "Note" and isinstance(v, int)])
    stacking_note = None
    if stacked_contraventions >= 2:
        stacking_note = (
            f"WARNING: {stacked_contraventions} independent regulatory contraventions identified. "
            "In enforcement proceedings, penalties may be stacked (applied cumulatively) "
            "for each contravention. The total regulatory exposure reflects the sum of "
            "all applicable maximum penalties."
        )

    # Combine for backwards compatibility but keep categories separate
    all_items = {**regulatory_items, **estimated_items}

    return {
        "items": all_items,
        "regulatory_items": regulatory_items,
        "estimated_items": estimated_items,
        "total_maximum_exposure": reg_total + est_total,
        "regulatory_total": reg_total,
        "estimated_total": est_total,
        "is_privacy_act_covered": is_covered,
        "stacked_contraventions": stacked_contraventions,
        "stacking_note": stacking_note,
    }


def _ai6_checklist(org_data: dict, policy_types: set[str]) -> list[dict]:
    """Map compliance to AI6 6 essential practices with weighted severity."""

    employee_count = org_data.get("employee_count", 10)
    is_large_org = employee_count >= 200

    overseas = org_data.get("ai_tools_overseas", [])
    has_overseas = any(o for o in overseas if o != "None — all data stays in Australia")
    has_sensitive = bool(
        {
            "Health Information",
            "Biometric Data",
            "Financial Data (transactions, account numbers)",
            "Children's Data (under 18)",
            "AI-Inferred Data (profiles, predictions)",
        }
        & set(org_data.get("data_types_processed", []))
    )
    has_tools = bool(org_data.get("ai_tools_in_use"))

    return [
        # =============================================
        # AI6 Practice 1: Understand Impacts and Plan Accordingly (4 items)
        # =============================================
        {
            "ai6_practice": "1. Understand Impacts and Plan Accordingly",
            "name": "AI tool register maintained",
            "description": "All AI tools in use are documented with data flows, risk ratings, and access controls.",
            "passed": has_tools and org_data.get("ai_access_restricted", False),
            "weight": 8,
            "severity": "high",
            "regulation": "AI6 Practice 1",
            "recommendation": "Create an AI tool register listing all tools, their purposes, data flows, and who has access. Restrict access by role.",
        },
        {
            "ai6_practice": "1. Understand Impacts and Plan Accordingly",
            "name": "Shadow AI controls in place",
            "description": "Organisation has technical or policy controls to detect and prevent unapproved AI tool usage.",
            "passed": org_data.get("shadow_ai_controls", False),
            "weight": 10,
            "severity": "critical",
            "regulation": "AI6 Practice 1, OAIC Oct 2024 Guidance",
            "recommendation": "Implement Shadow AI detection controls (DNS blocklists, proxy logs, endpoint monitoring). 80% of SME employees use unapproved AI tools.",
        },
        {
            "ai6_practice": "1. Understand Impacts and Plan Accordingly",
            "name": "Cross-border data flows mapped",
            "description": "Organisation knows which AI tools process data overseas and has assessed APP 8 obligations.",
            "passed": not has_overseas or org_data.get("vendor_dpa_in_place", False),
            "weight": 9,
            "severity": "critical" if has_overseas else "low",
            "regulation": "APP 8, Section 16C vicarious liability",
            "recommendation": "Map all AI tool data processing locations. Ensure DPAs are in place for overseas providers. Consider Australian-hosted alternatives for sensitive data.",
        },
        {
            "ai6_practice": "1. Understand Impacts and Plan Accordingly",
            "name": "AI prompts and outputs logged",
            "description": "AI interactions are logged for audit, incident investigation, and quality assurance.",
            "passed": org_data.get("ai_outputs_logged", False),
            "weight": 8 if is_large_org else 6,
            "severity": "medium",
            "regulation": "AI6 Practice 1, OAIC Guidance (accountability)",
            "recommendation": "Implement logging of AI prompts and outputs to support audit trails and incident investigation.",
        },
        # =============================================
        # AI6 Practice 2: Decide Who Is Accountable (3 items)
        # =============================================
        {
            "ai6_practice": "2. Decide Who Is Accountable",
            "name": "Named AI governance contact",
            "description": "A named individual is responsible for AI governance.",
            "passed": bool((org_data.get("ai_governance_contact") or "").strip()),
            "weight": 7,
            "severity": "high",
            "regulation": "AI Ethics Principle 8 (Accountability), AI6 Practice 2",
            "recommendation": "Designate a named person responsible for AI governance, incident response, and policy compliance.",
        },
        {
            "ai6_practice": "2. Decide Who Is Accountable",
            "name": "AI acceptable use policy exists",
            "description": "Organisation has an AI acceptable use policy.",
            "passed": "ai_acceptable_use" in policy_types,
            "weight": 9,
            "severity": "critical",
            "regulation": "AI6 Practice 2, OAIC Oct 2024 Guidance",
            "recommendation": "Generate an AI Acceptable Use Policy defining approved tools, prohibited uses, and data handling rules.",
        },
        {
            "ai6_practice": "2. Decide Who Is Accountable",
            "name": "Board/executive AI awareness",
            "description": "Board or senior leadership has been briefed on AI risks and governance obligations.",
            "passed": org_data.get("board_ai_awareness", False),
            "weight": 9 if (org_data.get("automated_decisions") or org_data.get("customer_facing_ai")) else 7,
            "severity": "critical" if (org_data.get("automated_decisions") and not org_data.get("board_ai_awareness")) else "high",
            "regulation": "Corporations Act s180 (duty of care), AI6 Practice 2",
            "recommendation": "Brief the board or senior leadership on AI risks, regulatory obligations, and the organisation's governance posture. Directors have a duty of care to understand material risks.",
        },
        # =============================================
        # AI6 Practice 3: Measure and Manage Risks (6 items)
        # =============================================
        {
            "ai6_practice": "3. Measure and Manage Risks",
            "name": "Privacy Impact Assessment conducted",
            "description": "A PIA has been conducted for AI tools processing personal information.",
            "passed": org_data.get("pia_conducted", False),
            "weight": 8,
            "severity": "high" if has_sensitive else "medium",
            "regulation": "OAIC Oct 2024 Guidance, APP 1",
            "recommendation": "Conduct a Privacy Impact Assessment before deploying AI systems that process personal information.",
        },
        {
            "ai6_practice": "3. Measure and Manage Risks",
            "name": "Data classification rules defined",
            "description": "Data classification tiers with AI-specific handling rules exist.",
            "passed": "data_classification" in policy_types,
            "weight": 8,
            "severity": "high",
            "regulation": "AI6 Practice 3, APPs 3, 6, 11",
            "recommendation": "Generate a Data Classification Policy defining what data can be used with which AI tools.",
        },
        {
            "ai6_practice": "3. Measure and Manage Risks",
            "name": "Data retention policy for AI outputs",
            "description": "Organisation has a policy for retaining and deleting AI-processed data and outputs.",
            "passed": org_data.get("has_data_retention_policy", False),
            "weight": 7,
            "severity": "high" if has_sensitive else "medium",
            "regulation": "APP 11 (destruction/de-identification), AI6 Practice 3",
            "recommendation": "Establish a data retention policy covering AI outputs, prompt logs, and processed data. APP 11 requires destroying personal information no longer needed.",
        },
        {
            "ai6_practice": "3. Measure and Manage Risks",
            "name": "Data retention period meets APP 11 minimisation",
            "description": "AI data retention period is proportionate and meets APP 11 data minimisation requirements.",
            "passed": org_data.get("has_data_retention_policy", False) and org_data.get("data_retention_period") in ("30_days", "90_days", "1_year"),
            "weight": 5,
            "severity": "medium" if has_sensitive else "low",
            "regulation": "APP 11 (destruction/de-identification)",
            "recommendation": "Reduce AI data retention to under 1 year. APP 11 requires destroying personal information no longer needed.",
        },
        {
            "ai6_practice": "3. Measure and Manage Risks",
            "name": "Incident response plan exists",
            "description": "AI incident response procedures are documented.",
            "passed": "incident_response" in policy_types,
            "weight": 8,
            "severity": "high",
            "regulation": "NDB Scheme, AI6 Practice 3",
            "recommendation": "Generate an AI Incident Response Plan covering detection, containment, OAIC notification, and recovery.",
        },
        {
            "ai6_practice": "3. Measure and Manage Risks",
            "name": "Incident response tested",
            "description": "Incident response procedures tested via tabletop exercise in past 12 months.",
            "passed": org_data.get("incident_response_tested", False),
            "weight": 5,
            "severity": "medium",
            "regulation": "AI6 Practice 3, OAIC Guidance (incident preparedness)",
            "recommendation": "Conduct a tabletop exercise simulating an AI-related data breach to test your response procedures.",
        },
        {
            "ai6_practice": "3. Measure and Manage Risks",
            "name": "Vendor Data Processing Agreements in place",
            "description": "DPAs exist with AI tool vendors for cross-border data protection.",
            "passed": not has_overseas or org_data.get("vendor_dpa_in_place", False),
            "weight": 7,
            "severity": "critical" if has_overseas else "low",
            "regulation": "APP 8, Section 16C",
            "recommendation": "Establish Data Processing Agreements with all AI vendors processing data overseas. You are vicariously liable under s16C.",
        },
        # =============================================
        # AI6 Practice 4: Share Information (3 items)
        # =============================================
        {
            "ai6_practice": "4. Share Information",
            "name": "Published privacy policy",
            "description": "Organisation has a published privacy policy covering AI data processing.",
            "passed": org_data.get("has_privacy_policy", False),
            "weight": 8,
            "severity": "critical"
            if (org_data.get("revenue_exceeds_threshold") or org_data.get("trades_in_personal_info"))
            else "high",
            "regulation": "APP 1.3-1.6, POLA Act 2024",
            "recommendation": "Publish a privacy policy that covers how personal information is collected, used, and disclosed through AI systems. Required under APP 1 and must include automated decision disclosure by December 2026.",
        },
        {
            "ai6_practice": "4. Share Information",
            "name": "POLA Act automated decision disclosure ready",
            "description": "Privacy policy discloses automated decision-making as required by December 2026.",
            "passed": (
                not org_data.get("automated_decisions", False)
                or (org_data.get("has_privacy_policy", False) and org_data.get("pia_conducted", False))
            ),
            "weight": 9,
            "severity": "critical" if org_data.get("automated_decisions") else "low",
            "regulation": "POLA Act 2024, APP 1.7-1.9 (commences Dec 2026)",
            "recommendation": "Update privacy policy to disclose: types of personal info used, types of automated decisions, and whether they significantly affect individuals. Deadline: 10 December 2026.",
        },
        {
            "ai6_practice": "4. Share Information",
            "name": "ACL compliance for AI-generated content",
            "description": "AI-generated customer-facing content is reviewed for accuracy before publication.",
            "passed": (
                not org_data.get("customer_facing_ai", False) or org_data.get("ai_generated_content_reviewed", False)
            ),
            "weight": 8,
            "severity": "critical"
            if org_data.get("customer_facing_ai") and not org_data.get("ai_generated_content_reviewed")
            else "low",
            "regulation": "ACL s18 (misleading conduct), Consumer Guarantees ss54-56",
            "recommendation": "Implement human review of all AI-generated customer-facing content. ACL s18 is strict liability — no intent required.",
        },
        {
            "ai6_practice": "4. Share Information",
            "name": "APP 5 — Notification of AI data collection",
            "description": "Individuals are notified when their personal information is collected for AI processing.",
            "passed": org_data.get("consent_mechanism_exists", False) and org_data.get("has_privacy_policy", False),
            "weight": 7,
            "severity": "high" if has_sensitive else "medium",
            "regulation": "APP 5 (notification of collection)",
            "recommendation": "Notify individuals at or before the time of collection that their data may be processed by AI. Include purpose, AI tool identity, and overseas disclosure in the notification.",
        },
        {
            "ai6_practice": "4. Share Information",
            "name": "APP 7 — Direct marketing consent for AI-generated communications",
            "description": "AI-generated marketing complies with direct marketing consent requirements.",
            "passed": (
                not org_data.get("ai_in_marketing", False) or org_data.get("consent_mechanism_exists", False)
            ),
            "weight": 7,
            "severity": "high" if org_data.get("ai_in_marketing") else "low",
            "regulation": "APP 7 (direct marketing)",
            "recommendation": "Ensure AI-generated marketing communications comply with APP 7 opt-out requirements. Individuals must be able to opt out of direct marketing at any time.",
        },
        {
            "ai6_practice": "4. Share Information",
            "name": "AI use disclosed to customers",
            "description": "Customers are informed when interacting with AI systems (chatbots, recommendations, AI-generated content).",
            "passed": (
                not org_data.get("customer_facing_ai", False) or org_data.get("ai_disclosure_to_customers", False)
            ),
            "weight": 8,
            "severity": "high" if org_data.get("customer_facing_ai") else "low",
            "regulation": "POLA Act 2024 s15, AI Ethics Principle 4 (Transparency)",
            "recommendation": "Disclose to customers when they are interacting with AI. Label chatbots, AI-generated recommendations, and AI-authored content clearly.",
        },
        # =============================================
        # AI6 Practice 5: Test and Monitor (7 items)
        # =============================================
        {
            "ai6_practice": "5. Test and Monitor",
            "name": "Human oversight for high-impact AI decisions",
            "description": "Human review is mandatory before AI-assisted decisions affecting individuals are finalised.",
            "passed": (
                not org_data.get("automated_decisions", False)
                or (
                    org_data.get("human_review_available", False)
                    and org_data.get("pia_conducted", False)
                    and "ai_acceptable_use" in policy_types
                )
            ),
            "weight": 10,
            "severity": "critical" if _has_high_impact(org_data) else "medium",
            "regulation": "AI Ethics Principles 1, 3, 7; POLA Act 2024",
            "recommendation": "Implement mandatory human review for all AI-assisted decisions affecting employment, credit, insurance, or access to services.",
        },
        {
            "ai6_practice": "5. Test and Monitor",
            "name": "Bias and fairness testing conducted",
            "description": "AI outputs assessed for bias against protected attributes (age, gender, race, disability).",
            "passed": org_data.get("bias_testing_conducted", False),
            "weight": 9,
            "severity": "critical" if org_data.get("automated_decisions") or org_data.get("ai_profiling_or_eligibility") else "high",
            "regulation": "AI Ethics Principle 2 (Fairness), Anti-Discrimination Act, POLA Act Tranche 2",
            "recommendation": "Conduct bias and fairness testing on AI systems, especially those making decisions about individuals. Test against protected attributes under Australian anti-discrimination law.",
        },
        {
            "ai6_practice": "5. Test and Monitor",
            "name": "Consent mechanisms for AI data processing",
            "description": "Organisation obtains consent before processing personal information through AI tools.",
            "passed": org_data.get("consent_mechanism_exists", False),
            "weight": 8,
            "severity": "high" if has_sensitive else "medium",
            "regulation": "APPs 3, 6 (consent for collection and use), AI Ethics Principle 2",
            "recommendation": "Implement consent mechanisms (notice, opt-in/opt-out) for collecting and processing personal information through AI tools.",
        },
        {
            "ai6_practice": "5. Test and Monitor",
            "name": "AI access restricted by role",
            "description": "AI tool access is role-based, not universal across all employees.",
            "passed": org_data.get("ai_access_restricted", False),
            "weight": 8 if is_large_org else 6,
            "severity": "medium",
            "regulation": "AI6 Practice 5, ACSC Essential Eight (application control)",
            "recommendation": "Restrict AI tool access by role to minimise risk of sensitive data exposure. Not all employees need access to all AI capabilities.",
        },
        {
            "ai6_practice": "5. Test and Monitor",
            "name": "NDB scheme — AI breach notification process",
            "description": "Organisation has a process for notifying the OAIC within 72 hours if an AI system is involved in a data breach.",
            "passed": org_data.get("ndb_ai_process", False),
            "weight": 8,
            "severity": "high",
            "regulation": "Privacy Act Part IIIC (NDB Scheme), OAIC Guidance",
            "recommendation": "Establish a documented process for notifying the OAIC and affected individuals within 72 hours when an AI system is involved in a data breach.",
        },
        {
            "ai6_practice": "5. Test and Monitor",
            "name": "Essential Eight controls applied to AI systems",
            "description": "ACSC Essential Eight security controls (application control, patching, MFA) extended to AI tools and ML libraries.",
            "passed": org_data.get("essential_eight_applied", False),
            "weight": 7,
            "severity": "high",
            "regulation": "ACSC Essential Eight, AI6 Practice 5",
            "recommendation": "Apply Essential Eight controls to AI systems: application whitelisting for AI tools, patch ML libraries, enforce MFA on AI platform accounts, restrict admin privileges.",
        },
        {
            "ai6_practice": "5. Test and Monitor",
            "name": "AI incident register maintained",
            "description": "Organisation maintains a dedicated AI incident register separate from general IT incidents.",
            "passed": org_data.get("ai_incident_register", False),
            "weight": 6,
            "severity": "medium",
            "regulation": "AI6 Practice 5, OAIC Guidance (incident management)",
            "recommendation": "Maintain a dedicated AI incident register tracking bias events, hallucinations, data leakage, and prompt injection attempts for pattern analysis.",
        },
        # =============================================
        # AI6 Practice 6: Maintain Human Control (5 items)
        # =============================================
        {
            "ai6_practice": "6. Maintain Human Control",
            "name": "Vendor AI clauses reviewed",
            "description": "Vendor contracts reviewed for AI-specific clauses (model training opt-out, sub-processor lists, IP).",
            "passed": org_data.get("vendor_ai_clauses_reviewed", False),
            "weight": 6,
            "severity": "high" if has_overseas else "medium",
            "regulation": "APP 8, OAIC Oct 2024 Guidance",
            "recommendation": "Review all AI vendor contracts for model-training opt-out, sub-processor disclosures, and IP ownership clauses.",
        },
        {
            "ai6_practice": "6. Maintain Human Control",
            "name": "Data minimisation practices for AI",
            "description": "Organisation minimises personal information in AI prompts and inputs.",
            "passed": org_data.get("ai_access_restricted", False) and org_data.get("ai_outputs_logged", False),
            "weight": 5,
            "severity": "medium",
            "regulation": "APP 3 (data minimisation), OAIC Oct 2024 Guidance",
            "recommendation": "Implement practices to minimise personal information in AI prompts. Train staff to anonymise or de-identify data before AI processing.",
        },
        # (AI6 Practice 6 continued)
        {
            "ai6_practice": "6. Maintain Human Control",
            "name": "Staff AI training scheduled",
            "description": "Regular AI and privacy training is scheduled for staff.",
            "passed": org_data.get("training_frequency", "never") != "never",
            "weight": 6,
            "severity": "medium",
            "regulation": "OAIC Guidance (recommends bi-annual), AI6 Practice 6",
            "recommendation": "Schedule at minimum bi-annual staff training on AI usage policies and privacy obligations.",
        },
        {
            "ai6_practice": "6. Maintain Human Control",
            "name": "Training frequency meets OAIC recommendation",
            "description": "Staff training occurs at least bi-annually as recommended by the OAIC.",
            "passed": org_data.get("training_frequency") in ("monthly", "quarterly", "biannually", "on_policy_change"),
            "weight": 7 if (is_large_org and (org_data.get("customer_facing_ai") or org_data.get("automated_decisions"))) else 4,
            "severity": "high" if (is_large_org and (org_data.get("customer_facing_ai") or org_data.get("automated_decisions"))) else "low",
            "regulation": "OAIC Oct 2024 Guidance",
            "recommendation": "Increase training frequency to at least bi-annually per OAIC recommendation.",
        },
        {
            "ai6_practice": "6. Maintain Human Control",
            "name": "Existing IT security policies foundation",
            "description": "Organisation has existing IT security policies to build AI governance on.",
            "passed": org_data.get("existing_it_policies", False),
            "weight": 3,
            "severity": "low",
            "regulation": "AI6 Practice 6, ACSC Essential Eight",
            "recommendation": "Develop foundational IT security policies. AI governance should build on existing security foundations.",
        },
        {
            "ai6_practice": "6. Maintain Human Control",
            "name": "APP 2 — Anonymity/pseudonymity option for AI interactions",
            "description": "Individuals can interact with AI systems anonymously or pseudonymously where practicable.",
            "passed": org_data.get("has_privacy_policy", False),
            "weight": 5,
            "severity": "medium",
            "regulation": "APP 2 (anonymity and pseudonymity)",
            "recommendation": "Where practicable, allow individuals to interact with AI systems without identifying themselves. Assess which AI interactions require identification.",
        },
        {
            "ai6_practice": "6. Maintain Human Control",
            "name": "APP 10 — Quality assurance for AI-processed data",
            "description": "Organisation ensures personal information processed by AI is accurate, up-to-date, and complete.",
            "passed": org_data.get("ai_generated_content_reviewed", False) and org_data.get("ai_outputs_logged", False),
            "weight": 6,
            "severity": "medium",
            "regulation": "APP 10 (quality of personal information)",
            "recommendation": "Implement quality assurance processes for personal information processed by AI. AI outputs should be verified for accuracy before being used in decision-making.",
        },
        {
            "ai6_practice": "6. Maintain Human Control",
            "name": "APP 12 — Access to AI-processed personal information",
            "description": "Individuals can access personal information that AI systems hold or have generated about them.",
            "passed": org_data.get("human_review_available", False),
            "weight": 7,
            "severity": "high",
            "regulation": "APP 12 (access to personal information)",
            "recommendation": "Ensure individuals can request access to personal information AI systems hold about them, including AI-inferred profiles and predictions.",
        },
        {
            "ai6_practice": "6. Maintain Human Control",
            "name": "APP 13 — Correction of AI-processed personal information",
            "description": "Individuals can request correction of inaccurate personal information processed by AI.",
            "passed": org_data.get("human_review_available", False),
            "weight": 7,
            "severity": "high",
            "regulation": "APP 13 (correction of personal information)",
            "recommendation": "Establish a process for individuals to request correction of inaccurate AI-generated or AI-processed personal information.",
        },
        {
            "ai6_practice": "6. Maintain Human Control",
            "name": "AI supply chain assessed",
            "description": "Organisation has assessed the AI supply chain (sub-processors, model providers, data sources).",
            "passed": org_data.get("ai_supply_chain_assessed", False),
            "weight": 6,
            "severity": "high" if has_overseas else "medium",
            "regulation": "APP 8, AI6 Practice 6",
            "recommendation": "Map and assess your AI supply chain including model providers, sub-processors, and training data sources. Understand downstream data flows.",
        },
        {
            "ai6_practice": "6. Maintain Human Control",
            "name": "Vendor audit rights in AI contracts",
            "description": "Contracts with AI vendors include audit or inspection rights.",
            "passed": org_data.get("vendor_audit_rights", False),
            "weight": 5,
            "severity": "medium",
            "regulation": "APP 8, OAIC Guidance (vendor management)",
            "recommendation": "Include audit and inspection rights in AI vendor contracts to verify compliance with data processing agreements and security requirements.",
        },
        {
            "ai6_practice": "6. Maintain Human Control",
            "name": "Copyright and IP risk assessed for AI outputs",
            "description": "Organisation has assessed copyright ownership and IP risks of AI-generated content.",
            "passed": org_data.get("ai_copyright_assessed", False),
            "weight": 5,
            "severity": "medium" if org_data.get("ai_in_marketing") or org_data.get("customer_facing_ai") else "low",
            "regulation": "Copyright Act 1968, AI Ethics Principle 4",
            "recommendation": "Assess copyright ownership of AI-generated works. Under the Copyright Act 1968, AI-generated content may lack copyright protection — do not rely on it as proprietary IP.",
        },
        {
            "ai6_practice": "6. Maintain Human Control",
            "name": "POLA Act Tranche 2 awareness",
            "description": "Organisation is aware of upcoming Tranche 2 requirements for high-risk AI systems.",
            "passed": org_data.get("tranche2_aware", False),
            "weight": 5,
            "severity": "medium",
            "regulation": "POLA Act 2024 (Tranche 2)",
            "recommendation": "Monitor POLA Act Tranche 2 developments. Prepare for potential mandatory conformity assessments, high-risk AI registers, and enhanced transparency obligations.",
        },
        {
            "ai6_practice": "6. Maintain Human Control",
            "name": "Cross-border data flows mapped for AI tools",
            "description": "Organisation has mapped which AI tools store or process data outside Australia.",
            "passed": not has_overseas or org_data.get("data_overseas_mapped", False),
            "weight": 7,
            "severity": "high" if has_overseas else "low",
            "regulation": "APP 8 (cross-border disclosure)",
            "recommendation": "Map all AI tools that process or store data outside Australia. Document data centre locations, sub-processors, and applicable data protection laws.",
        },
    ]


def _has_high_impact(org_data: dict) -> bool:
    high_impact = {
        "Employment decisions (hiring, performance, termination)",
        "Credit or lending decisions",
        "Insurance underwriting or claims",
    }
    return bool(high_impact & set(org_data.get("automated_decision_types", [])))


def calculate_compliance_score(org_data: dict, policy_types: set[str]) -> dict:
    """Calculate weighted compliance score with penalty exposure quantification."""

    checklist = _ai6_checklist(org_data, policy_types)
    penalty_exposure = _estimate_max_penalty_exposure(org_data)

    total_weight = sum(item["weight"] for item in checklist)
    earned_weight = sum(item["weight"] for item in checklist if item["passed"])
    score_percentage = round((earned_weight / total_weight) * 100) if total_weight > 0 else 0

    passed = sum(1 for item in checklist if item["passed"])
    total = len(checklist)

    # Compounding penalty: systemic governance failure
    failed_count = total - passed
    if total > 0 and (failed_count / total) > 0.6:
        score_percentage = round(score_percentage * 0.9)

    # Group by AI6 practice
    by_practice: dict[str, dict[str, list | int]] = {}
    for item in checklist:
        practice = item["ai6_practice"]
        if practice not in by_practice:
            by_practice[practice] = {"items": [], "passed": 0, "total": 0}
        by_practice[practice]["items"].append(item)  # type: ignore[union-attr]
        by_practice[practice]["total"] += 1  # type: ignore[operator]
        if item["passed"]:
            by_practice[practice]["passed"] += 1  # type: ignore[operator]

    # Identify critical gaps
    critical_gaps = [item for item in checklist if not item["passed"] and item["severity"] == "critical"]
    high_gaps = [item for item in checklist if not item["passed"] and item["severity"] == "high"]

    # Risk rating
    if score_percentage >= 80 and not critical_gaps:
        risk_rating = "LOW"
        risk_description = (
            "Organisation has strong AI governance foundations. Continue monitoring regulatory developments."
        )
    elif score_percentage >= 60 and len(critical_gaps) <= 1:
        risk_rating = "MEDIUM"
        risk_description = (
            "Organisation has moderate AI governance. Address critical gaps before December 2026 POLA Act deadline."
        )
    elif score_percentage >= 40:
        risk_rating = "HIGH"
        risk_description = "Significant governance gaps exist. Immediate action required to reduce regulatory exposure."
    else:
        risk_rating = "CRITICAL"
        risk_description = "Organisation has minimal AI governance. Urgent action required — current posture exposes the business to substantial penalties."

    return {
        "checklist": checklist,
        "by_practice": by_practice,
        "passed": passed,
        "total": total,
        "score_percentage": score_percentage,
        "total_weight": total_weight,
        "earned_weight": earned_weight,
        "risk_rating": risk_rating,
        "risk_description": risk_description,
        "critical_gaps": critical_gaps,
        "high_gaps": high_gaps,
        "penalty_exposure": penalty_exposure,
    }


# --- Benchmarking ---

# Industry baseline compliance scores — used for benchmarking when < 3 real entries exist.
#
# Methodology: Scores are estimated based on the following sources and assumptions:
#   1. OAIC NDB Report H2 2024 — breach notification rates by industry sector
#   2. ACSC Cyber Security Survey 2024 — AI and security maturity by sector
#   3. AI6 Guidance adoption rates — estimated from OAIC compliance assessments
#   4. Industry regulatory burden — sectors with existing heavy regulation (finance,
#      healthcare, insurance) score higher due to pre-existing compliance infrastructure
#
# Each industry has 5 synthetic baseline scores representing the expected range of
# compliance maturity across typical SMEs in that sector. Scores are pre-POLA Act
# (before December 2026 obligations commence) — expect a sector-wide shift of +5-10%
# as organisations prepare for POLA Act Tranche 1 commencement.
#
# Last reviewed: March 2026. Review annually or when major regulatory changes occur.
_INDUSTRY_BASELINES = {
    "healthcare": [55, 62, 48, 70, 58],
    "finance": [68, 72, 65, 60, 75],
    "education": [42, 50, 38, 55, 45],
    "technology": [65, 70, 58, 72, 68],
    "retail": [35, 42, 50, 38, 45],
    "government": [60, 55, 65, 70, 62],
    "legal": [58, 65, 52, 60, 55],
    "manufacturing": [40, 45, 35, 50, 42],
    "professional_services": [55, 60, 50, 65, 58],
    "not_for_profit": [38, 45, 42, 50, 35],
    "construction": [30, 38, 35, 42, 40],
    "media_entertainment": [48, 55, 52, 45, 50],
    "insurance": [62, 68, 58, 65, 70],
    "real_estate": [32, 40, 38, 45, 42],
    "mining_resources": [45, 50, 42, 55, 48],
    "agriculture": [28, 35, 32, 40, 38],
    "transport_logistics": [35, 42, 38, 48, 45],
    "other": [45, 50, 40, 55, 48],
}


def save_compliance_snapshot(db: Session, org_id: int, industry: str, score_result: dict) -> None:
    """Save a compliance score snapshot for benchmarking (one per org per day)."""
    import datetime as _dt

    from app.models import ComplianceSnapshot

    # Deduplicate: update existing snapshot for same org + same day (UTC)
    utc_now = _dt.datetime.now(_dt.timezone.utc)
    today_start = utc_now.replace(hour=0, minute=0, second=0, microsecond=0)
    today_end = today_start + _dt.timedelta(days=1)
    existing = (
        db.query(ComplianceSnapshot)
        .filter(
            ComplianceSnapshot.org_id == org_id,
            ComplianceSnapshot.created_at >= today_start,
            ComplianceSnapshot.created_at < today_end,
        )
        .first()
    )

    if existing:
        existing.score_percentage = score_result["score_percentage"]
        existing.risk_rating = score_result["risk_rating"]
        existing.passed = score_result["passed"]
        existing.total = score_result["total"]
        existing.penalty_exposure_total = score_result["penalty_exposure"]["total_maximum_exposure"]
    else:
        snapshot = ComplianceSnapshot(
            org_id=org_id,
            industry=industry,
            score_percentage=score_result["score_percentage"],
            risk_rating=score_result["risk_rating"],
            passed=score_result["passed"],
            total=score_result["total"],
            penalty_exposure_total=score_result["penalty_exposure"]["total_maximum_exposure"],
        )
        db.add(snapshot)

    try:
        db.commit()
    except Exception:
        db.rollback()
        raise


def get_industry_benchmarks(db: Session, industry: str, org_score: float) -> dict:
    """Get industry benchmark data including percentile ranking."""
    from app.models import ComplianceSnapshot

    snapshots = db.query(ComplianceSnapshot).filter(ComplianceSnapshot.industry == industry).all()

    scores: list[float] = [s.score_percentage for s in snapshots]  # type: ignore[misc]

    # Seed with baselines if fewer than 3 real entries
    if len(scores) < 3:
        baselines = _INDUSTRY_BASELINES.get(industry, _INDUSTRY_BASELINES["other"])
        scores = [*baselines, *scores]

    avg_score = round(sum(scores) / len(scores), 1) if scores else 0
    below_count = sum(1 for s in scores if s < org_score)
    percentile = round((below_count / len(scores)) * 100) if scores else 50

    # Score distribution buckets
    distribution = {"0-25": 0, "26-50": 0, "51-75": 0, "76-100": 0}
    for s in scores:
        if s <= 25:
            distribution["0-25"] += 1
        elif s <= 50:
            distribution["26-50"] += 1
        elif s <= 75:
            distribution["51-75"] += 1
        else:
            distribution["76-100"] += 1

    return {
        "industry": industry,
        "avg_score": avg_score,
        "org_count": len(scores),
        "percentile_rank": percentile,
        "score_distribution": distribution,
        "org_score": org_score,
        "gap_from_average": round(org_score - avg_score, 1),
    }
