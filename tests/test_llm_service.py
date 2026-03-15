from app.llm_service import _build_clause_prompt

SAMPLE_DATA = {
    "business_name": "Test Corp",
    "industry": "healthcare",
    "employee_count": 30,
    "revenue_exceeds_threshold": True,
    "ai_tools_in_use": ["ChatGPT", "Claude"],
    "data_types_processed": ["Health Information", "Personal Information"],
    "automated_decisions": True,
    "existing_it_policies": False,
    "training_frequency": "quarterly",
}


def test_build_clause_prompt_contains_org_details():
    prompt = _build_clause_prompt("ai_acceptable_use", SAMPLE_DATA, "Regulatory context here")
    assert "Test Corp" in prompt
    assert "healthcare" in prompt
    assert "Health Information" in prompt
    assert "Regulatory context here" in prompt


def test_build_clause_prompt_for_each_template():
    for template in ["ai_acceptable_use", "data_classification", "incident_response"]:
        prompt = _build_clause_prompt(template, SAMPLE_DATA, "context")
        assert len(prompt) > 100
