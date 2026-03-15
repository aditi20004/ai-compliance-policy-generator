import pytest

from app.questionnaire import QuestionnaireResponse


def _valid_data(**overrides):
    base = {
        "business_name": "Test Corp",
        "industry": "technology",
        "employee_count": 25,
        "annual_revenue": "3m_to_10m",
        "ai_tools_in_use": ["ChatGPT / OpenAI"],
        "ai_tools_overseas": ["ChatGPT / OpenAI (US)"],
        "shadow_ai_aware": True,
        "shadow_ai_controls": False,
        "customer_facing_ai": False,
        "ai_generated_content_reviewed": False,
        "automated_decisions": False,
        "automated_decision_types": [],
        "data_types_processed": ["Customer Data (purchase history, preferences)"],
        "trades_in_personal_info": False,
        "vendor_dpa_in_place": False,
        "pia_conducted": False,
        "existing_it_policies": True,
        "incident_response_tested": False,
        "training_frequency": "annually",
    }
    base.update(overrides)
    return base


def test_valid_questionnaire():
    r = QuestionnaireResponse(**_valid_data())
    assert r.business_name == "Test Corp"
    assert r.employee_count == 25
    assert r.revenue_exceeds_threshold is True


def test_abn_validation_valid():
    r = QuestionnaireResponse(**_valid_data(abn="51824753556"))
    assert r.abn == "51824753556"


def test_abn_validation_with_spaces():
    r = QuestionnaireResponse(**_valid_data(abn="51 824 753 556"))
    assert r.abn == "51824753556"


def test_abn_validation_invalid():
    with pytest.raises(ValueError):
        QuestionnaireResponse(**_valid_data(abn="123"))


def test_empty_ai_tools_accepted():
    """AI tools list can be empty (pre-adoption orgs)."""
    r = QuestionnaireResponse(**_valid_data(ai_tools_in_use=[]))
    assert r.ai_tools_in_use == []


def test_has_sensitive_data():
    r = QuestionnaireResponse(**_valid_data(data_types_processed=["Health Information"]))
    assert r.has_sensitive_data() is True


def test_no_sensitive_data():
    r = QuestionnaireResponse(**_valid_data(data_types_processed=["Publicly Available Data"]))
    assert r.has_sensitive_data() is False


def test_privacy_act_covered_by_revenue():
    r = QuestionnaireResponse(**_valid_data(annual_revenue="3m_to_10m"))
    assert r.is_privacy_act_covered() is True


def test_privacy_act_not_covered():
    r = QuestionnaireResponse(**_valid_data(annual_revenue="under_3m", trades_in_personal_info=False))
    assert r.is_privacy_act_covered() is False


def test_cross_border_risk():
    r = QuestionnaireResponse(**_valid_data(ai_tools_overseas=["ChatGPT / OpenAI (US)"]))
    assert r.has_cross_border_risk() is True


def test_no_cross_border_risk():
    r = QuestionnaireResponse(**_valid_data(ai_tools_overseas=["None — all data stays in Australia"]))
    assert r.has_cross_border_risk() is False


def test_shadow_ai_risk():
    r = QuestionnaireResponse(**_valid_data(shadow_ai_aware=True, shadow_ai_controls=False))
    assert r.has_shadow_ai_risk() is True


def test_acl_risk():
    r = QuestionnaireResponse(**_valid_data(customer_facing_ai=True, ai_generated_content_reviewed=False))
    assert r.has_acl_risk() is True
