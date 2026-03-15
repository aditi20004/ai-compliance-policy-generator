"""
Comprehensive tests for the compliance checker scoring engine.
Covers all checklist items, scoring algorithm, risk ratings,
penalty exposure, gap categorisation, policy effects, and benchmarks.
"""

from app.compliance_checker import (
    _INDUSTRY_BASELINES,
    ESTIMATED_COSTS,
    PENALTIES,
    _ai6_checklist,
    _estimate_max_penalty_exposure,
    calculate_compliance_score,
    get_industry_benchmarks,
    save_compliance_snapshot,
)

# --- Fixtures ---

SAMPLE_ORG = {
    "business_name": "Test Pty Ltd",
    "industry": "technology",
    "employee_count": 30,
    "annual_revenue": "3m_to_10m",
    "revenue_exceeds_threshold": True,
    "ai_tools_in_use": ["ChatGPT / OpenAI"],
    "ai_tools_overseas": ["ChatGPT / OpenAI (US)"],
    "shadow_ai_aware": True,
    "shadow_ai_controls": False,
    "customer_facing_ai": True,
    "ai_generated_content_reviewed": True,
    "ai_access_restricted": True,
    "ai_outputs_logged": False,
    "automated_decisions": True,
    "automated_decision_types": ["Employment decisions (hiring, performance, termination)"],
    "data_types_processed": [
        "Personal Information (names, emails, addresses)",
        "Customer Data (purchase history, preferences)",
    ],
    "trades_in_personal_info": False,
    "has_data_retention_policy": False,
    "consent_mechanism_exists": True,
    "vendor_dpa_in_place": False,
    "pia_conducted": False,
    "has_privacy_policy": True,
    "existing_it_policies": True,
    "incident_response_tested": False,
    "board_ai_awareness": False,
    "training_frequency": "quarterly",
    "ai_governance_contact": "Jane Smith",
}

FULLY_COMPLIANT_ORG = {
    "business_name": "Compliant Corp",
    "industry": "finance",
    "employee_count": 100,
    "annual_revenue": "10m_to_50m",
    "revenue_exceeds_threshold": True,
    "ai_tools_in_use": ["ChatGPT / OpenAI"],
    "ai_tools_overseas": ["None — all data stays in Australia"],
    "shadow_ai_aware": True,
    "shadow_ai_controls": True,
    "customer_facing_ai": True,
    "ai_generated_content_reviewed": True,
    "ai_access_restricted": True,
    "ai_outputs_logged": True,
    "automated_decisions": True,
    "automated_decision_types": ["Fraud detection"],
    "data_types_processed": ["Customer Data (purchase history, preferences)"],
    "trades_in_personal_info": False,
    "has_data_retention_policy": True,
    "consent_mechanism_exists": True,
    "vendor_dpa_in_place": True,
    "pia_conducted": True,
    "has_privacy_policy": True,
    "existing_it_policies": True,
    "incident_response_tested": True,
    "board_ai_awareness": True,
    "training_frequency": "quarterly",
    "ai_governance_contact": "CISO",
    "vendor_ai_clauses_reviewed": True,
    "data_retention_period": "1_year",
    # New GRC fields
    "bias_testing_conducted": True,
    "ai_profiling_or_eligibility": False,
    "ai_in_marketing": False,
    "ai_copyright_assessed": True,
    "human_review_available": True,
    "ndb_ai_process": True,
    "essential_eight_applied": True,
    "ai_incident_register": True,
    "vendor_audit_rights": True,
    "ai_disclosure_to_customers": True,
    "ai_supply_chain_assessed": True,
    "tranche2_aware": True,
    "data_overseas_mapped": True,
}

ZERO_COMPLIANCE_ORG = {
    "business_name": "No Governance LLC",
    "industry": "retail",
    "employee_count": 5,
    "annual_revenue": "under_3m",
    "revenue_exceeds_threshold": False,
    "ai_tools_in_use": [],
    "ai_tools_overseas": [],
    "shadow_ai_aware": False,
    "shadow_ai_controls": False,
    "customer_facing_ai": False,
    "ai_generated_content_reviewed": False,
    "ai_access_restricted": False,
    "ai_outputs_logged": False,
    "automated_decisions": False,
    "automated_decision_types": [],
    "data_types_processed": ["Publicly Available Data"],
    "trades_in_personal_info": False,
    "has_data_retention_policy": False,
    "consent_mechanism_exists": False,
    "vendor_dpa_in_place": False,
    "pia_conducted": False,
    "has_privacy_policy": False,
    "existing_it_policies": False,
    "incident_response_tested": False,
    "board_ai_awareness": False,
    "training_frequency": "never",
    "ai_governance_contact": "",
}

ALL_POLICY_TYPES = {
    "ai_acceptable_use",
    "data_classification",
    "incident_response",
    "vendor_risk_assessment",
    "ai_ethics_framework",
    "employee_ai_training",
    "ai_risk_register",
    "privacy_policy",
    "board_ai_briefing",
    "remediation_action_plan",
    "ai_transparency_statement",
    "ai_data_retention",
    "ai_procurement",
    "shadow_ai_playbook",
    "bias_audit_procedure",
    "statutory_tort_defence",
    "tranche2_readiness",
    "ai_tool_approval",
    "essential_eight_ai",
    "copyright_ip_policy",
    "ai_supply_chain_audit",
}


# ======================
# Checklist item count
# ======================


class TestChecklistStructure:
    def test_checklist_has_expected_items(self):
        items = _ai6_checklist(SAMPLE_ORG, set())
        assert len(items) >= 38  # expanded from 24 with GRC improvements

    def test_all_items_have_required_fields(self):
        items = _ai6_checklist(SAMPLE_ORG, set())
        for item in items:
            assert "ai6_practice" in item
            assert "name" in item
            assert "passed" in item
            assert "weight" in item
            assert "severity" in item
            assert "regulation" in item
            assert "recommendation" in item

    def test_six_practices_present(self):
        items = _ai6_checklist(SAMPLE_ORG, set())
        practices = {item["ai6_practice"] for item in items}
        assert len(practices) == 6


# ==================================
# Individual checklist item tests
# ==================================


class TestKnowYourAI:
    """AI6 Practice 1: Know Your AI (4 items)."""

    def test_tool_register_passes_when_tools_and_restricted(self):
        org = {**SAMPLE_ORG, "ai_tools_in_use": ["ChatGPT / OpenAI"], "ai_access_restricted": True}
        items = _ai6_checklist(org, set())
        item = next(i for i in items if i["name"] == "AI tool register maintained")
        assert item["passed"] is True

    def test_tool_register_fails_without_tools(self):
        org = {**SAMPLE_ORG, "ai_tools_in_use": []}
        items = _ai6_checklist(org, set())
        item = next(i for i in items if i["name"] == "AI tool register maintained")
        assert item["passed"] is False

    def test_shadow_ai_controls_passes(self):
        org = {**SAMPLE_ORG, "shadow_ai_controls": True}
        items = _ai6_checklist(org, set())
        item = next(i for i in items if i["name"] == "Shadow AI controls in place")
        assert item["passed"] is True

    def test_shadow_ai_controls_fails(self):
        org = {**SAMPLE_ORG, "shadow_ai_controls": False}
        items = _ai6_checklist(org, set())
        item = next(i for i in items if i["name"] == "Shadow AI controls in place")
        assert item["passed"] is False

    def test_cross_border_passes_with_dpa(self):
        org = {**SAMPLE_ORG, "ai_tools_overseas": ["ChatGPT / OpenAI (US)"], "vendor_dpa_in_place": True}
        items = _ai6_checklist(org, set())
        item = next(i for i in items if i["name"] == "Cross-border data flows mapped")
        assert item["passed"] is True

    def test_cross_border_passes_no_overseas(self):
        org = {**SAMPLE_ORG, "ai_tools_overseas": ["None — all data stays in Australia"]}
        items = _ai6_checklist(org, set())
        item = next(i for i in items if i["name"] == "Cross-border data flows mapped")
        assert item["passed"] is True

    def test_cross_border_fails_overseas_no_dpa(self):
        org = {**SAMPLE_ORG, "ai_tools_overseas": ["ChatGPT / OpenAI (US)"], "vendor_dpa_in_place": False}
        items = _ai6_checklist(org, set())
        item = next(i for i in items if i["name"] == "Cross-border data flows mapped")
        assert item["passed"] is False

    def test_ai_prompts_logged_passes(self):
        org = {**SAMPLE_ORG, "ai_outputs_logged": True}
        items = _ai6_checklist(org, set())
        item = next(i for i in items if i["name"] == "AI prompts and outputs logged")
        assert item["passed"] is True

    def test_ai_prompts_logged_fails(self):
        org = {**SAMPLE_ORG, "ai_outputs_logged": False}
        items = _ai6_checklist(org, set())
        item = next(i for i in items if i["name"] == "AI prompts and outputs logged")
        assert item["passed"] is False


class TestBeAccountable:
    """AI6 Practice 2: Be Accountable (3 items)."""

    def test_governance_contact_passes(self):
        org = {**SAMPLE_ORG, "ai_governance_contact": "Jane Smith"}
        items = _ai6_checklist(org, set())
        item = next(i for i in items if i["name"] == "Named AI governance contact")
        assert item["passed"] is True

    def test_governance_contact_fails_empty(self):
        org = {**SAMPLE_ORG, "ai_governance_contact": ""}
        items = _ai6_checklist(org, set())
        item = next(i for i in items if i["name"] == "Named AI governance contact")
        assert item["passed"] is False

    def test_acceptable_use_policy_passes(self):
        items = _ai6_checklist(SAMPLE_ORG, {"ai_acceptable_use"})
        item = next(i for i in items if i["name"] == "AI acceptable use policy exists")
        assert item["passed"] is True

    def test_acceptable_use_policy_fails(self):
        items = _ai6_checklist(SAMPLE_ORG, set())
        item = next(i for i in items if i["name"] == "AI acceptable use policy exists")
        assert item["passed"] is False

    def test_board_awareness_passes(self):
        org = {**SAMPLE_ORG, "board_ai_awareness": True}
        items = _ai6_checklist(org, set())
        item = next(i for i in items if i["name"] == "Board/executive AI awareness")
        assert item["passed"] is True


class TestManageRisks:
    """AI6 Practice 3: Manage Risks (6 items)."""

    def test_pia_conducted_passes(self):
        org = {**SAMPLE_ORG, "pia_conducted": True}
        items = _ai6_checklist(org, set())
        item = next(i for i in items if i["name"] == "Privacy Impact Assessment conducted")
        assert item["passed"] is True

    def test_data_classification_passes_with_policy(self):
        items = _ai6_checklist(SAMPLE_ORG, {"data_classification"})
        item = next(i for i in items if i["name"] == "Data classification rules defined")
        assert item["passed"] is True

    def test_data_retention_passes(self):
        org = {**SAMPLE_ORG, "has_data_retention_policy": True}
        items = _ai6_checklist(org, set())
        item = next(i for i in items if i["name"] == "Data retention policy for AI outputs")
        assert item["passed"] is True

    def test_incident_response_passes_with_policy(self):
        items = _ai6_checklist(SAMPLE_ORG, {"incident_response"})
        item = next(i for i in items if i["name"] == "Incident response plan exists")
        assert item["passed"] is True

    def test_incident_response_tested_passes(self):
        org = {**SAMPLE_ORG, "incident_response_tested": True}
        items = _ai6_checklist(org, set())
        item = next(i for i in items if i["name"] == "Incident response tested")
        assert item["passed"] is True

    def test_vendor_dpa_passes_with_overseas_and_dpa(self):
        org = {**SAMPLE_ORG, "ai_tools_overseas": ["ChatGPT / OpenAI (US)"], "vendor_dpa_in_place": True}
        items = _ai6_checklist(org, set())
        item = next(i for i in items if i["name"] == "Vendor Data Processing Agreements in place")
        assert item["passed"] is True


class TestBeTransparent:
    """AI6 Practice 4: Be Transparent (3 items)."""

    def test_privacy_policy_passes(self):
        org = {**SAMPLE_ORG, "has_privacy_policy": True}
        items = _ai6_checklist(org, set())
        item = next(i for i in items if i["name"] == "Published privacy policy")
        assert item["passed"] is True

    def test_pola_disclosure_passes_no_automated(self):
        org = {**SAMPLE_ORG, "automated_decisions": False}
        items = _ai6_checklist(org, set())
        item = next(i for i in items if i["name"] == "POLA Act automated decision disclosure ready")
        assert item["passed"] is True

    def test_pola_disclosure_passes_with_policy_and_pia(self):
        org = {**SAMPLE_ORG, "automated_decisions": True, "has_privacy_policy": True, "pia_conducted": True}
        items = _ai6_checklist(org, set())
        item = next(i for i in items if i["name"] == "POLA Act automated decision disclosure ready")
        assert item["passed"] is True

    def test_acl_passes_when_no_customer_ai(self):
        org = {**SAMPLE_ORG, "customer_facing_ai": False}
        items = _ai6_checklist(org, set())
        item = next(i for i in items if i["name"] == "ACL compliance for AI-generated content")
        assert item["passed"] is True

    def test_acl_passes_when_reviewed(self):
        org = {**SAMPLE_ORG, "customer_facing_ai": True, "ai_generated_content_reviewed": True}
        items = _ai6_checklist(org, set())
        item = next(i for i in items if i["name"] == "ACL compliance for AI-generated content")
        assert item["passed"] is True

    def test_acl_fails_customer_ai_no_review(self):
        org = {**SAMPLE_ORG, "customer_facing_ai": True, "ai_generated_content_reviewed": False}
        items = _ai6_checklist(org, set())
        item = next(i for i in items if i["name"] == "ACL compliance for AI-generated content")
        assert item["passed"] is False


class TestSafetyFairness:
    """AI6 Practice 5: Safety & Fairness (expanded with bias, NDB, E8, incidents)."""

    def test_human_oversight_passes_no_automated(self):
        org = {**SAMPLE_ORG, "automated_decisions": False}
        items = _ai6_checklist(org, set())
        item = next(i for i in items if i["name"] == "Human oversight for high-impact AI decisions")
        assert item["passed"] is True

    def test_consent_mechanism_passes(self):
        org = {**SAMPLE_ORG, "consent_mechanism_exists": True}
        items = _ai6_checklist(org, set())
        item = next(i for i in items if i["name"] == "Consent mechanisms for AI data processing")
        assert item["passed"] is True

    def test_ai_access_restricted_passes(self):
        org = {**SAMPLE_ORG, "ai_access_restricted": True}
        items = _ai6_checklist(org, set())
        item = next(i for i in items if i["name"] == "AI access restricted by role")
        assert item["passed"] is True


class TestEngageReview:
    """AI6 Practice 6: Engage & Review (expanded with APPs, supply chain, copyright, tranche2)."""

    def test_training_scheduled_passes(self):
        org = {**SAMPLE_ORG, "training_frequency": "quarterly"}
        items = _ai6_checklist(org, set())
        item = next(i for i in items if i["name"] == "Staff AI training scheduled")
        assert item["passed"] is True

    def test_training_scheduled_fails_never(self):
        org = {**SAMPLE_ORG, "training_frequency": "never"}
        items = _ai6_checklist(org, set())
        item = next(i for i in items if i["name"] == "Staff AI training scheduled")
        assert item["passed"] is False

    def test_training_frequency_meets_oaic(self):
        org = {**SAMPLE_ORG, "training_frequency": "biannually"}
        items = _ai6_checklist(org, set())
        item = next(i for i in items if i["name"] == "Training frequency meets OAIC recommendation")
        assert item["passed"] is True

    def test_training_frequency_fails_annually(self):
        org = {**SAMPLE_ORG, "training_frequency": "annually"}
        items = _ai6_checklist(org, set())
        item = next(i for i in items if i["name"] == "Training frequency meets OAIC recommendation")
        assert item["passed"] is False

    def test_existing_it_policies_passes(self):
        org = {**SAMPLE_ORG, "existing_it_policies": True}
        items = _ai6_checklist(org, set())
        item = next(i for i in items if i["name"] == "Existing IT security policies foundation")
        assert item["passed"] is True


# ========================
# Scoring algorithm tests
# ========================


class TestScoringAlgorithm:
    def test_fully_compliant_100_percent(self):
        result = calculate_compliance_score(FULLY_COMPLIANT_ORG, ALL_POLICY_TYPES)
        assert result["score_percentage"] == 100
        assert result["passed"] == result["total"]

    def test_zero_compliance_low_score(self):
        result = calculate_compliance_score(ZERO_COMPLIANCE_ORG, set())
        assert result["score_percentage"] < 40

    def test_weighted_calculation(self):
        result = calculate_compliance_score(SAMPLE_ORG, set())
        total_weight = sum(i["weight"] for i in result["checklist"])
        earned_weight = sum(i["weight"] for i in result["checklist"] if i["passed"])
        expected = round((earned_weight / total_weight) * 100)
        assert result["score_percentage"] == expected
        assert result["total_weight"] == total_weight
        assert result["earned_weight"] == earned_weight

    def test_policies_improve_score(self):
        score_without = calculate_compliance_score(SAMPLE_ORG, set())["score_percentage"]
        score_with = calculate_compliance_score(SAMPLE_ORG, ALL_POLICY_TYPES)["score_percentage"]
        assert score_with > score_without


# ========================
# Risk rating thresholds
# ========================


class TestRiskRating:
    def test_low_risk_at_high_score_no_critical(self):
        result = calculate_compliance_score(FULLY_COMPLIANT_ORG, ALL_POLICY_TYPES)
        assert result["risk_rating"] == "LOW"

    def test_critical_risk_below_40(self):
        result = calculate_compliance_score(ZERO_COMPLIANCE_ORG, set())
        assert result["risk_rating"] == "CRITICAL"

    def test_critical_gaps_prevent_low_rating(self):
        # Org with high score but critical gaps (shadow_ai_controls=False is critical)
        org = {**FULLY_COMPLIANT_ORG, "shadow_ai_controls": False}
        result = calculate_compliance_score(org, ALL_POLICY_TYPES)
        # Removing a critical control must produce at least one critical gap
        assert len(result["critical_gaps"]) > 0, "Expected critical gaps when shadow_ai_controls=False"
        # Even with high score, having critical gaps should prevent LOW rating
        assert result["risk_rating"] != "LOW"


# ========================
# Penalty exposure tests
# ========================


class TestPenaltyExposure:
    def test_statutory_tort_always_present(self):
        # Even for zero-compliance org under small business exemption
        exposure = _estimate_max_penalty_exposure(ZERO_COMPLIANCE_ORG)
        assert "Statutory tort — estimated damages (any organisation)" in exposure["items"]
        assert "Statutory tort — estimated damages (any organisation)" in exposure["estimated_items"]
        assert exposure["estimated_items"]["Statutory tort — estimated damages (any organisation)"] == ESTIMATED_COSTS["statutory_tort"]

    def test_shadow_ai_triggers_estimated_cost(self):
        org = {**SAMPLE_ORG, "shadow_ai_controls": False}
        exposure = _estimate_max_penalty_exposure(org)
        assert "Shadow AI data breach cost — estimated (IBM 2025)" in exposure["items"]
        assert "Shadow AI data breach cost — estimated (IBM 2025)" in exposure["estimated_items"]
        assert exposure["estimated_items"]["Shadow AI data breach cost — estimated (IBM 2025)"] == ESTIMATED_COSTS["shadow_ai_sme"]

    def test_no_shadow_ai_cost_with_controls(self):
        org = {**SAMPLE_ORG, "shadow_ai_controls": True}
        exposure = _estimate_max_penalty_exposure(org)
        assert "Shadow AI data breach cost — estimated (IBM 2025)" not in exposure["items"]

    def test_customer_ai_without_review_triggers_acl(self):
        org = {**SAMPLE_ORG, "customer_facing_ai": True, "ai_generated_content_reviewed": False}
        exposure = _estimate_max_penalty_exposure(org)
        assert "ACL misleading conduct risk" in exposure["items"]
        assert "ACL misleading conduct risk" in exposure["regulatory_items"]

    def test_automated_decisions_without_pia_triggers_tier1(self):
        org = {**SAMPLE_ORG, "automated_decisions": True, "pia_conducted": False, "revenue_exceeds_threshold": True}
        exposure = _estimate_max_penalty_exposure(org)
        assert "POLA Act non-compliance (Tier 1)" in exposure["regulatory_items"]
        assert exposure["regulatory_items"]["POLA Act non-compliance (Tier 1)"] == PENALTIES["tier_1_admin"]

    def test_small_business_exemption_note(self):
        org = {**ZERO_COMPLIANCE_ORG, "revenue_exceeds_threshold": False, "trades_in_personal_info": False}
        exposure = _estimate_max_penalty_exposure(org)
        assert "Note" in exposure["regulatory_items"]
        assert exposure["is_privacy_act_covered"] is False

    def test_regulatory_and_estimated_totals_separate(self):
        org = {**SAMPLE_ORG, "shadow_ai_controls": False, "revenue_exceeds_threshold": True,
               "has_privacy_policy": False, "automated_decisions": True, "pia_conducted": False}
        exposure = _estimate_max_penalty_exposure(org)
        assert exposure["regulatory_total"] > 0
        assert exposure["estimated_total"] > 0
        assert exposure["total_maximum_exposure"] == exposure["regulatory_total"] + exposure["estimated_total"]


# ========================
# Gap categorisation tests
# ========================


class TestGapCategorisation:
    def test_critical_gaps_are_critical_severity(self):
        result = calculate_compliance_score(SAMPLE_ORG, set())
        for gap in result["critical_gaps"]:
            assert gap["severity"] == "critical"

    def test_high_gaps_are_high_severity(self):
        result = calculate_compliance_score(SAMPLE_ORG, set())
        for gap in result["high_gaps"]:
            assert gap["severity"] == "high"

    def test_no_gaps_when_fully_compliant(self):
        result = calculate_compliance_score(FULLY_COMPLIANT_ORG, ALL_POLICY_TYPES)
        assert len(result["critical_gaps"]) == 0
        assert len(result["high_gaps"]) == 0

    def test_by_practice_structure(self):
        result = calculate_compliance_score(SAMPLE_ORG, set())
        assert len(result["by_practice"]) == 6
        for practice_name, practice_data in result["by_practice"].items():
            assert "items" in practice_data
            assert "passed" in practice_data
            assert "total" in practice_data
            assert practice_data["total"] > 0


# ========================
# Industry benchmarks
# ========================


class TestIndustryBenchmarks:
    def test_baseline_returned_for_known_industry(self):
        # Use None db — will use baselines since no real snapshots
        from unittest.mock import MagicMock

        mock_db = MagicMock()
        mock_db.query.return_value.filter.return_value.all.return_value = []
        benchmarks = get_industry_benchmarks(mock_db, "healthcare", 60)
        assert benchmarks["industry"] == "healthcare"
        assert benchmarks["avg_score"] > 0
        assert benchmarks["org_count"] > 0

    def test_baseline_for_unknown_industry_uses_other(self):
        from unittest.mock import MagicMock

        mock_db = MagicMock()
        mock_db.query.return_value.filter.return_value.all.return_value = []
        benchmarks = get_industry_benchmarks(mock_db, "unknown_industry", 50)
        assert benchmarks["industry"] == "unknown_industry"
        assert benchmarks["org_count"] == len(_INDUSTRY_BASELINES["other"])

    def test_percentile_ranking(self):
        from unittest.mock import MagicMock

        mock_db = MagicMock()
        mock_db.query.return_value.filter.return_value.all.return_value = []
        # Score of 90 should be high percentile in most industries
        benchmarks = get_industry_benchmarks(mock_db, "retail", 90)
        assert benchmarks["percentile_rank"] >= 50

    def test_score_distribution_buckets(self):
        from unittest.mock import MagicMock

        mock_db = MagicMock()
        mock_db.query.return_value.filter.return_value.all.return_value = []
        benchmarks = get_industry_benchmarks(mock_db, "technology", 65)
        dist = benchmarks["score_distribution"]
        assert "0-25" in dist
        assert "26-50" in dist
        assert "51-75" in dist
        assert "76-100" in dist
        assert sum(dist.values()) == benchmarks["org_count"]


# ========================
# Additional penalty tests
# ========================


class TestPenaltyExposureExtended:
    def test_cross_border_no_dpa_triggers_tier2(self):
        org = {**SAMPLE_ORG, "ai_tools_overseas": ["ChatGPT / OpenAI (US)"], "vendor_dpa_in_place": False,
               "revenue_exceeds_threshold": True}
        exposure = _estimate_max_penalty_exposure(org)
        assert "APP 8 cross-border non-compliance (Tier 2)" in exposure["regulatory_items"]
        assert exposure["regulatory_items"]["APP 8 cross-border non-compliance (Tier 2)"] == PENALTIES["tier_2_interference"]

    def test_cross_border_with_dpa_no_tier2(self):
        org = {**SAMPLE_ORG, "ai_tools_overseas": ["ChatGPT / OpenAI (US)"], "vendor_dpa_in_place": True,
               "revenue_exceeds_threshold": True}
        exposure = _estimate_max_penalty_exposure(org)
        assert "APP 8 cross-border non-compliance (Tier 2)" not in exposure.get("regulatory_items", {})

    def test_no_privacy_policy_triggers_tier1(self):
        org = {**SAMPLE_ORG, "has_privacy_policy": False, "revenue_exceeds_threshold": True}
        exposure = _estimate_max_penalty_exposure(org)
        assert "APP 1 no privacy policy (Tier 1)" in exposure["regulatory_items"]
        assert exposure["regulatory_items"]["APP 1 no privacy policy (Tier 1)"] == PENALTIES["tier_1_admin"]

    def test_privacy_policy_present_no_tier1(self):
        org = {**SAMPLE_ORG, "has_privacy_policy": True, "revenue_exceeds_threshold": True}
        exposure = _estimate_max_penalty_exposure(org)
        assert "APP 1 no privacy policy (Tier 1)" not in exposure.get("regulatory_items", {})

    def test_ai_inferred_data_triggers_sensitive_tier2(self):
        org = {**SAMPLE_ORG, "data_types_processed": ["AI-Inferred Data (profiles, predictions)"],
               "ai_access_restricted": False, "pia_conducted": False, "revenue_exceeds_threshold": True}
        exposure = _estimate_max_penalty_exposure(org)
        assert "Privacy Act interference (Tier 2)" in exposure["regulatory_items"]


# ========================
# Human oversight logic
# ========================


class TestHumanOversight:
    def test_passes_with_pia_and_policy(self):
        org = {**SAMPLE_ORG, "automated_decisions": True, "pia_conducted": True}
        items = _ai6_checklist(org, {"ai_acceptable_use"})
        item = next(i for i in items if i["name"] == "Human oversight for high-impact AI decisions")
        assert item["passed"] is True

    def test_fails_without_pia(self):
        org = {**SAMPLE_ORG, "automated_decisions": True, "pia_conducted": False}
        items = _ai6_checklist(org, {"ai_acceptable_use"})
        item = next(i for i in items if i["name"] == "Human oversight for high-impact AI decisions")
        assert item["passed"] is False

    def test_fails_without_policy(self):
        org = {**SAMPLE_ORG, "automated_decisions": True, "pia_conducted": True}
        items = _ai6_checklist(org, set())  # no policies
        item = next(i for i in items if i["name"] == "Human oversight for high-impact AI decisions")
        assert item["passed"] is False

    def test_high_impact_severity_is_critical(self):
        org = {**SAMPLE_ORG, "automated_decisions": True,
               "automated_decision_types": ["Employment decisions (hiring, performance, termination)"]}
        items = _ai6_checklist(org, set())
        item = next(i for i in items if i["name"] == "Human oversight for high-impact AI decisions")
        assert item["severity"] == "critical"

    def test_low_impact_severity_is_medium(self):
        org = {**SAMPLE_ORG, "automated_decisions": True,
               "automated_decision_types": ["Content moderation"]}
        items = _ai6_checklist(org, set())
        item = next(i for i in items if i["name"] == "Human oversight for high-impact AI decisions")
        assert item["severity"] == "medium"


# ========================
# Snapshot deduplication
# ========================


class TestSnapshotDedup:
    def test_save_snapshot_updates_existing_same_day(self):
        """Running compliance twice on the same day updates the existing snapshot."""
        from app.database import SessionLocal, init_db
        from app.models import ComplianceSnapshot, Organisation

        init_db()
        db = SessionLocal()
        try:
            # Create a real org to satisfy FK constraint
            org = Organisation(
                business_name="Snapshot Test Corp",
                industry="technology",
                employee_count=10,
            )
            db.add(org)
            db.commit()
            db.refresh(org)
            oid = org.id

            # First save
            result_v1 = calculate_compliance_score(SAMPLE_ORG, set())
            save_compliance_snapshot(db, oid, "technology", result_v1)

            count_after_first = db.query(ComplianceSnapshot).filter(
                ComplianceSnapshot.org_id == oid
            ).count()

            # Second save (same day) — should UPDATE, not INSERT
            result_v2 = calculate_compliance_score(
                {**SAMPLE_ORG, "shadow_ai_controls": True}, {"ai_acceptable_use"}
            )
            save_compliance_snapshot(db, oid, "technology", result_v2)

            count_after_second = db.query(ComplianceSnapshot).filter(
                ComplianceSnapshot.org_id == oid
            ).count()

            assert count_after_second == count_after_first, (
                "Second save on same day should update, not create duplicate"
            )

            # Verify the score was updated to the newer value
            latest = db.query(ComplianceSnapshot).filter(
                ComplianceSnapshot.org_id == oid
            ).first()
            assert latest.score_percentage == result_v2["score_percentage"]
        finally:
            db.close()


# ========================
# Governance contact validation
# ========================


class TestGovernanceContactValidation:
    def test_whitespace_only_contact_fails(self):
        """Whitespace-only governance contact should NOT pass the checklist item."""
        org = {**SAMPLE_ORG, "ai_governance_contact": "   "}
        items = _ai6_checklist(org, set())
        item = next(i for i in items if i["name"] == "Named AI governance contact")
        assert item["passed"] is False

    def test_none_contact_fails(self):
        org = {**SAMPLE_ORG, "ai_governance_contact": None}
        items = _ai6_checklist(org, set())
        item = next(i for i in items if i["name"] == "Named AI governance contact")
        assert item["passed"] is False

    def test_valid_contact_passes(self):
        org = {**SAMPLE_ORG, "ai_governance_contact": "Jane Smith"}
        items = _ai6_checklist(org, set())
        item = next(i for i in items if i["name"] == "Named AI governance contact")
        assert item["passed"] is True


# ========================
# Overseas data mixed mode
# ========================


class TestOverseasMixedMode:
    def test_mixed_overseas_and_none_detects_overseas(self):
        """Selecting both an overseas provider AND 'None' should still flag overseas."""
        org = {**SAMPLE_ORG,
               "ai_tools_overseas": ["ChatGPT / OpenAI (US)", "None — all data stays in Australia"],
               "vendor_dpa_in_place": False}
        items = _ai6_checklist(org, set())
        cross_border = next(i for i in items if i["name"] == "Cross-border data flows mapped")
        assert cross_border["passed"] is False, (
            "Mixed selection with real overseas provider should fail without DPA"
        )

    def test_only_none_has_no_overseas(self):
        """Selecting only 'None' should correctly pass cross-border check."""
        org = {**SAMPLE_ORG,
               "ai_tools_overseas": ["None — all data stays in Australia"]}
        items = _ai6_checklist(org, set())
        cross_border = next(i for i in items if i["name"] == "Cross-border data flows mapped")
        assert cross_border["passed"] is True


# ========================
# New GRC checklist items
# ========================


class TestBiasFairnessTesting:
    def test_bias_testing_passes_when_conducted(self):
        org = {**SAMPLE_ORG, "bias_testing_conducted": True}
        items = _ai6_checklist(org, set())
        item = next(i for i in items if i["name"] == "Bias and fairness testing conducted")
        assert item["passed"] is True

    def test_bias_testing_fails_when_not_conducted(self):
        org = {**SAMPLE_ORG, "bias_testing_conducted": False}
        items = _ai6_checklist(org, set())
        item = next(i for i in items if i["name"] == "Bias and fairness testing conducted")
        assert item["passed"] is False

    def test_bias_critical_when_automated_decisions(self):
        org = {**SAMPLE_ORG, "automated_decisions": True, "bias_testing_conducted": False}
        items = _ai6_checklist(org, set())
        item = next(i for i in items if i["name"] == "Bias and fairness testing conducted")
        assert item["severity"] == "critical"


class TestNDBAndEssentialEight:
    def test_ndb_passes_when_process_exists(self):
        org = {**SAMPLE_ORG, "ndb_ai_process": True}
        items = _ai6_checklist(org, set())
        item = next(i for i in items if i["name"] == "NDB scheme — AI breach notification process")
        assert item["passed"] is True

    def test_ndb_fails_when_no_process(self):
        org = {**SAMPLE_ORG, "ndb_ai_process": False}
        items = _ai6_checklist(org, set())
        item = next(i for i in items if i["name"] == "NDB scheme — AI breach notification process")
        assert item["passed"] is False

    def test_essential_eight_passes(self):
        org = {**SAMPLE_ORG, "essential_eight_applied": True}
        items = _ai6_checklist(org, set())
        item = next(i for i in items if i["name"] == "Essential Eight controls applied to AI systems")
        assert item["passed"] is True

    def test_ai_incident_register_passes(self):
        org = {**SAMPLE_ORG, "ai_incident_register": True}
        items = _ai6_checklist(org, set())
        item = next(i for i in items if i["name"] == "AI incident register maintained")
        assert item["passed"] is True


class TestAPPCoverage:
    def test_app5_notification_passes(self):
        org = {**SAMPLE_ORG, "consent_mechanism_exists": True, "has_privacy_policy": True}
        items = _ai6_checklist(org, set())
        item = next(i for i in items if i["name"] == "APP 5 — Notification of AI data collection")
        assert item["passed"] is True

    def test_app5_notification_fails(self):
        org = {**SAMPLE_ORG, "consent_mechanism_exists": False, "has_privacy_policy": True}
        items = _ai6_checklist(org, set())
        item = next(i for i in items if i["name"] == "APP 5 — Notification of AI data collection")
        assert item["passed"] is False

    def test_app7_marketing_passes_no_marketing(self):
        org = {**SAMPLE_ORG, "ai_in_marketing": False}
        items = _ai6_checklist(org, set())
        item = next(i for i in items if i["name"] == "APP 7 — Direct marketing consent for AI-generated communications")
        assert item["passed"] is True

    def test_app7_marketing_fails_no_consent(self):
        org = {**SAMPLE_ORG, "ai_in_marketing": True, "consent_mechanism_exists": False}
        items = _ai6_checklist(org, set())
        item = next(i for i in items if i["name"] == "APP 7 — Direct marketing consent for AI-generated communications")
        assert item["passed"] is False

    def test_app12_access_passes(self):
        org = {**SAMPLE_ORG, "human_review_available": True}
        items = _ai6_checklist(org, set())
        item = next(i for i in items if i["name"] == "APP 12 — Access to AI-processed personal information")
        assert item["passed"] is True

    def test_app13_correction_passes(self):
        org = {**SAMPLE_ORG, "human_review_available": True}
        items = _ai6_checklist(org, set())
        item = next(i for i in items if i["name"] == "APP 13 — Correction of AI-processed personal information")
        assert item["passed"] is True

    def test_ai_disclosure_passes(self):
        org = {**SAMPLE_ORG, "customer_facing_ai": True, "ai_disclosure_to_customers": True}
        items = _ai6_checklist(org, set())
        item = next(i for i in items if i["name"] == "AI use disclosed to customers")
        assert item["passed"] is True

    def test_ai_disclosure_fails(self):
        org = {**SAMPLE_ORG, "customer_facing_ai": True, "ai_disclosure_to_customers": False}
        items = _ai6_checklist(org, set())
        item = next(i for i in items if i["name"] == "AI use disclosed to customers")
        assert item["passed"] is False


class TestSupplyChainAndCopyright:
    def test_supply_chain_passes(self):
        org = {**SAMPLE_ORG, "ai_supply_chain_assessed": True}
        items = _ai6_checklist(org, set())
        item = next(i for i in items if i["name"] == "AI supply chain assessed")
        assert item["passed"] is True

    def test_vendor_audit_rights_passes(self):
        org = {**SAMPLE_ORG, "vendor_audit_rights": True}
        items = _ai6_checklist(org, set())
        item = next(i for i in items if i["name"] == "Vendor audit rights in AI contracts")
        assert item["passed"] is True

    def test_copyright_passes(self):
        org = {**SAMPLE_ORG, "ai_copyright_assessed": True}
        items = _ai6_checklist(org, set())
        item = next(i for i in items if i["name"] == "Copyright and IP risk assessed for AI outputs")
        assert item["passed"] is True

    def test_tranche2_passes(self):
        org = {**SAMPLE_ORG, "tranche2_aware": True}
        items = _ai6_checklist(org, set())
        item = next(i for i in items if i["name"] == "POLA Act Tranche 2 awareness")
        assert item["passed"] is True


class TestPenaltyStacking:
    def test_stacking_warning_when_multiple_contraventions(self):
        org = {**SAMPLE_ORG, "revenue_exceeds_threshold": True, "has_privacy_policy": False,
               "automated_decisions": True, "pia_conducted": False, "vendor_dpa_in_place": False,
               "ai_tools_overseas": ["ChatGPT / OpenAI (US)"], "ndb_ai_process": False}
        exposure = _estimate_max_penalty_exposure(org)
        assert exposure["stacked_contraventions"] >= 2
        assert exposure["stacking_note"] is not None
        assert "WARNING" in exposure["stacking_note"]

    def test_no_stacking_note_with_single_contravention(self):
        org = {**FULLY_COMPLIANT_ORG, "has_privacy_policy": False, "revenue_exceeds_threshold": True,
               "ndb_ai_process": True}
        exposure = _estimate_max_penalty_exposure(org)
        # May have 0 or 1 regulatory items; stacking note only for >= 2
        if exposure["stacked_contraventions"] < 2:
            assert exposure["stacking_note"] is None

    def test_ndb_penalty_triggered(self):
        org = {**SAMPLE_ORG, "revenue_exceeds_threshold": True, "ndb_ai_process": False}
        exposure = _estimate_max_penalty_exposure(org)
        assert "NDB scheme non-compliance (failure to notify)" in exposure["regulatory_items"]
