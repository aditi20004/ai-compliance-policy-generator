import pytest
from fastapi.testclient import TestClient

from app.database import init_db
from app.main import app


@pytest.fixture(autouse=True)
def setup_db():
    init_db()


client = TestClient(app)


def _questionnaire_data(**overrides):
    base = {
        "business_name": "API Test Corp",
        "industry": "technology",
        "employee_count": 10,
        "annual_revenue": "under_3m",
        "ai_tools_in_use": ["ChatGPT / OpenAI"],
        "ai_tools_overseas": ["None — all data stays in Australia"],
        "shadow_ai_aware": False,
        "shadow_ai_controls": False,
        "customer_facing_ai": False,
        "ai_generated_content_reviewed": False,
        "automated_decisions": False,
        "automated_decision_types": [],
        "data_types_processed": ["Customer Data (purchase history, preferences)"],
        "trades_in_personal_info": False,
        "data_retention_period": "no_defined_period",
        "vendor_dpa_in_place": False,
        "vendor_ai_clauses_reviewed": False,
        "pia_conducted": False,
        "existing_it_policies": True,
        "incident_response_tested": False,
        "training_frequency": "annually",
    }
    base.update(overrides)
    return base


def _submit_questionnaire():
    data = _questionnaire_data()
    response = client.post("/api/questionnaire", json=data)
    assert response.status_code == 200
    return response.json()["org_id"]


def test_list_questions():
    response = client.get("/api/questions")
    assert response.status_code == 200
    questions = response.json()
    assert len(questions) >= 20


def test_submit_questionnaire():
    org_id = _submit_questionnaire()
    assert org_id >= 1


def test_generate_policy():
    org_id = _submit_questionnaire()
    response = client.post(f"/api/generate/ai_acceptable_use?org_id={org_id}&output_format=markdown")
    assert response.status_code == 200
    result = response.json()
    assert "policy_id" in result
    assert "content_hash" in result


def test_generate_invalid_template():
    org_id = _submit_questionnaire()
    response = client.post(f"/api/generate/invalid_type?org_id={org_id}")
    assert response.status_code == 400


def test_list_policies():
    org_id = _submit_questionnaire()
    client.post(f"/api/generate/ai_acceptable_use?org_id={org_id}&output_format=markdown")
    response = client.get(f"/api/policies/{org_id}")
    assert response.status_code == 200
    assert len(response.json()) >= 1


def test_audit_log():
    _submit_questionnaire()
    response = client.get("/api/audit-log")
    assert response.status_code == 200
    assert len(response.json()) >= 1


def test_get_organisation():
    org_id = _submit_questionnaire()
    response = client.get(f"/api/organisation/{org_id}")
    assert response.status_code == 200
    data = response.json()
    assert data["business_name"] == "API Test Corp"
    assert data["industry"] == "technology"


def test_get_organisation_not_found():
    response = client.get("/api/organisation/99999")
    assert response.status_code == 404


def test_download_policy():
    org_id = _submit_questionnaire()
    gen = client.post(f"/api/generate/ai_acceptable_use?org_id={org_id}&output_format=markdown")
    assert gen.status_code == 200
    policy_id = gen.json()["policy_id"]

    response = client.get(f"/api/download/{policy_id}")
    assert response.status_code == 200
    assert len(response.content) > 0


def test_download_policy_not_found():
    response = client.get("/api/download/99999")
    assert response.status_code == 404


def test_benchmarks_endpoint():
    response = client.get("/api/benchmarks/technology?org_score=65")
    assert response.status_code == 200
    data = response.json()
    assert "avg_score" in data
    assert "percentile_rank" in data
    assert "score_distribution" in data
    assert data["industry"] == "technology"


def test_generate_report():
    org_id = _submit_questionnaire()
    response = client.post(f"/api/generate-report/{org_id}")
    assert response.status_code == 200
    data = response.json()
    assert "policy_id" in data
    assert "content_hash" in data


def test_generate_report_not_found():
    response = client.post("/api/generate-report/99999")
    assert response.status_code == 404


def test_generate_remediation():
    org_id = _submit_questionnaire()
    response = client.post(f"/api/generate-remediation/{org_id}")
    assert response.status_code == 200
    data = response.json()
    assert "policy_id" in data
    assert "content_hash" in data


def test_generate_remediation_not_found():
    response = client.post("/api/generate-remediation/99999")
    assert response.status_code == 404
