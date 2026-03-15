import pytest

from app.generator import TEMPLATE_TYPES, build_template_context, render_policy_text

SAMPLE_DATA = {
    "business_name": "Acme Pty Ltd",
    "abn": "51824753556",
    "industry": "technology",
    "employee_count": 50,
    "annual_revenue": "3m_to_10m",
    "revenue_exceeds_threshold": True,
    "ai_tools_in_use": ["ChatGPT / OpenAI", "GitHub Copilot"],
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
    "data_retention_period": "no_defined_period",
    "consent_mechanism_exists": True,
    "vendor_dpa_in_place": False,
    "pia_conducted": False,
    "has_privacy_policy": True,
    "vendor_ai_clauses_reviewed": False,
    "existing_it_policies": True,
    "incident_response_tested": False,
    "board_ai_awareness": False,
    "training_frequency": "quarterly",
    "ai_governance_contact": "Jane Smith",
}


def test_build_template_context():
    ctx = build_template_context(SAMPLE_DATA)
    assert ctx["business_name"] == "Acme Pty Ltd"
    assert "effective_date" in ctx
    assert ctx["version"] == "1.0"


@pytest.mark.parametrize(
    "template_type", [t for t in TEMPLATE_TYPES.keys() if t not in ("remediation_action_plan", "board_ai_briefing")]
)
def test_render_all_templates(template_type):
    ctx = build_template_context(SAMPLE_DATA)
    result = render_policy_text(template_type, ctx)
    assert "Acme Pty Ltd" in result
    assert len(result) > 500


def test_render_board_briefing():
    from app.generator import build_board_briefing_context

    ctx = build_board_briefing_context(SAMPLE_DATA, {"ai_acceptable_use", "data_classification"})
    result = render_policy_text("board_ai_briefing", ctx)
    assert "Acme Pty Ltd" in result
    assert "Board" in result


def test_render_invalid_template():
    with pytest.raises(ValueError):
        render_policy_text("nonexistent", {})


def test_conditional_privacy_act_section():
    ctx = build_template_context(SAMPLE_DATA)
    result = render_policy_text("ai_acceptable_use", ctx)
    assert "Privacy Act" in result


def test_conditional_automated_decisions():
    ctx = build_template_context(SAMPLE_DATA)
    result = render_policy_text("ai_acceptable_use", ctx)
    assert "human review" in result.lower() or "Human" in result


def test_no_privacy_act_when_below_threshold():
    data = {**SAMPLE_DATA, "revenue_exceeds_threshold": False, "trades_in_personal_info": False}
    ctx = build_template_context(data)
    result = render_policy_text("ai_acceptable_use", ctx)
    # Below threshold: should show small business exemption language, not full compliance
    assert "small business exemption" in result.lower() or "exemption" in result.lower()
    assert len(result) > 100


def test_privacy_policy_template():
    ctx = build_template_context(SAMPLE_DATA)
    result = render_policy_text("privacy_policy", ctx)
    assert "Privacy Policy" in result
    assert "APP" in result
    assert "POLA" in result


def test_compliance_checker_new_items():
    from app.compliance_checker import calculate_compliance_score

    policy_types = {"ai_acceptable_use", "data_classification", "incident_response"}
    result = calculate_compliance_score(SAMPLE_DATA, policy_types)
    # Should have 40 items (expanded checklist with GRC improvements)
    assert result["total"] == 40
    # Shadow AI controls = False should now FAIL (fixed logic)
    shadow_item = next(i for i in result["checklist"] if i["name"] == "Shadow AI controls in place")
    assert shadow_item["passed"] is False


# --- Template Conditional Rendering Tests ---


def test_health_data_shows_in_training_template():
    """Health Information string triggers health data guidance in employee training."""
    data = {**SAMPLE_DATA, "data_types_processed": ["Health Information"]}
    ctx = build_template_context(data)
    result = render_policy_text("employee_ai_training", ctx)
    assert "Health Data" in result
    assert "My Health Records Act 2012" in result


def test_financial_data_shows_in_training_template():
    """Financial Data string triggers financial guidance in employee training."""
    data = {**SAMPLE_DATA, "data_types_processed": ["Financial Data (transactions, account numbers)"]}
    ctx = build_template_context(data)
    result = render_policy_text("employee_ai_training", ctx)
    assert "Financial Data" in result
    assert "Finance Manager" in result


def test_childrens_data_shows_in_training_template():
    """Children's Data string triggers children's data prohibition."""
    data = {**SAMPLE_DATA, "data_types_processed": ["Children's Data (under 18)"]}
    ctx = build_template_context(data)
    result = render_policy_text("employee_ai_training", ctx)
    assert "under 18" in result
    assert "NEVER" in result


def test_health_data_shows_in_risk_register():
    """Health Information triggers health data risk row in risk register."""
    data = {**SAMPLE_DATA, "data_types_processed": ["Health Information"]}
    ctx = build_template_context(data)
    result = render_policy_text("ai_risk_register", ctx)
    assert "Health data" in result
    assert "DP-03" in result


def test_data_classification_uses_correct_data_type_strings():
    """Data classification template uses exact questionnaire data type strings."""
    data = {
        **SAMPLE_DATA,
        "data_types_processed": [
            "Personal Information (names, emails, addresses)",
            "Financial Data (transactions, account numbers)",
            "Customer Data (purchase history, preferences)",
            "Employee Data (HR records, performance)",
        ],
    }
    ctx = build_template_context(data)
    result = render_policy_text("data_classification", ctx)
    assert "Personal information of customers" in result
    assert "Financial records, budgets" in result
    assert "Customer account details" in result
    assert "Employee performance reviews" in result


def test_empty_ai_tools_shows_pre_adoption_message():
    """Employee training template shows pre-adoption message when no tools approved."""
    data = {**SAMPLE_DATA, "ai_tools_in_use": []}
    ctx = build_template_context(data)
    result = render_policy_text("employee_ai_training", ctx)
    assert "not yet formally approved" in result


def test_none_industry_does_not_crash_report():
    """Generator handles None industry without crashing."""
    data = {**SAMPLE_DATA, "industry": None}
    ctx = build_template_context(data)
    # Should not raise AttributeError
    result = render_policy_text("ai_acceptable_use", ctx)
    assert len(result) > 100


def test_transparency_statement_safeguard_table():
    """AI transparency statement safeguard table uses actual context variables."""
    ctx = build_template_context(SAMPLE_DATA)
    result = render_policy_text("ai_transparency_statement", ctx)
    # existing_it_policies=True should show "In place" for AUP row
    assert "In place" in result
    # ai_access_restricted=True should show "Yes" for role-based access
    assert "| Yes |" in result or "Yes" in result
    # ai_outputs_logged=False should show "In progress"
    assert "In progress" in result


# --- Penalty Exposure Tests ---


def test_sensitive_data_with_controls_no_tier2_penalty():
    """Sensitive data WITH proper controls should NOT trigger Tier 2 penalty."""
    from app.compliance_checker import _estimate_max_penalty_exposure

    data = {
        **SAMPLE_DATA,
        "data_types_processed": ["Health Information"],
        "ai_access_restricted": True,
        "pia_conducted": True,
    }
    result = _estimate_max_penalty_exposure(data)
    assert "Privacy Act interference (Tier 2)" not in result["items"]


def test_sensitive_data_without_controls_triggers_tier2():
    """Sensitive data WITHOUT controls SHOULD trigger Tier 2 penalty."""
    from app.compliance_checker import _estimate_max_penalty_exposure

    data = {
        **SAMPLE_DATA,
        "data_types_processed": ["Health Information"],
        "ai_access_restricted": False,
        "pia_conducted": False,
    }
    result = _estimate_max_penalty_exposure(data)
    assert "Privacy Act interference (Tier 2)" in result["items"]


def test_health_data_triggers_privacy_act_coverage():
    """Health data processing triggers Privacy Act coverage regardless of revenue."""
    from app.compliance_checker import _estimate_max_penalty_exposure

    data = {
        **SAMPLE_DATA,
        "revenue_exceeds_threshold": False,
        "trades_in_personal_info": False,
        "data_types_processed": ["Health Information"],
        "has_privacy_policy": True,
        "pia_conducted": False,
        "ai_access_restricted": False,
    }
    result = _estimate_max_penalty_exposure(data)
    assert result["is_privacy_act_covered"] is True


# --- Data Classification Section 6 Tests ---


def test_data_classification_section6_personal_info():
    """Section 6 renders details for Personal Information data type."""
    data = {**SAMPLE_DATA, "data_types_processed": ["Personal Information (names, emails, addresses)"]}
    ctx = build_template_context(data)
    result = render_policy_text("data_classification", ctx)
    assert "Anonymise before AI processing" in result


def test_data_classification_section6_financial_data():
    """Section 6 renders details for Financial Data type."""
    data = {**SAMPLE_DATA, "data_types_processed": ["Financial Data (transactions, account numbers)"]}
    ctx = build_template_context(data)
    result = render_policy_text("data_classification", ctx)
    assert "No external AI tools" in result


def test_data_classification_section6_trade_secrets():
    """Section 6 renders details for Trade Secrets / IP data type."""
    data = {**SAMPLE_DATA, "data_types_processed": ["Trade Secrets / IP"]}
    ctx = build_template_context(data)
    result = render_policy_text("data_classification", ctx)
    assert "extreme caution" in result


def test_data_classification_section6_ai_inferred():
    """Section 6 renders details for AI-Inferred Data type."""
    data = {**SAMPLE_DATA, "data_types_processed": ["AI-Inferred Data (profiles, predictions)"]}
    ctx = build_template_context(data)
    result = render_policy_text("data_classification", ctx)
    assert "explainable" in result


def test_data_classification_section6_customer_data():
    """Section 6 renders details for Customer Data type."""
    data = {**SAMPLE_DATA, "data_types_processed": ["Customer Data (purchase history, preferences)"]}
    ctx = build_template_context(data)
    result = render_policy_text("data_classification", ctx)
    assert "purpose limitation" in result


def test_data_classification_section6_employee_data():
    """Section 6 renders details for Employee Data type."""
    data = {**SAMPLE_DATA, "data_types_processed": ["Employee Data (HR records, performance)"]}
    ctx = build_template_context(data)
    result = render_policy_text("data_classification", ctx)
    assert "HR approval" in result


# --- AI6 Practice Assignment Tests ---


def test_vendor_clauses_assigned_to_practice_6():
    """Vendor AI clauses item should be under Practice 6 (Maintain Human Control)."""
    from app.compliance_checker import _ai6_checklist

    items = _ai6_checklist(SAMPLE_DATA, set())
    vendor_item = next(i for i in items if i["name"] == "Vendor AI clauses reviewed")
    assert vendor_item["ai6_practice"] == "6. Maintain Human Control"


def test_data_minimisation_assigned_to_practice_6():
    """Data minimisation item should be under Practice 6 (Maintain Human Control)."""
    from app.compliance_checker import _ai6_checklist

    items = _ai6_checklist(SAMPLE_DATA, set())
    item = next(i for i in items if i["name"] == "Data minimisation practices for AI")
    assert item["ai6_practice"] == "6. Maintain Human Control"


def test_on_policy_change_meets_training_recommendation():
    """Training frequency 'on_policy_change' should pass OAIC recommendation check."""
    from app.compliance_checker import _ai6_checklist

    data = {**SAMPLE_DATA, "training_frequency": "on_policy_change"}
    items = _ai6_checklist(data, set())
    item = next(i for i in items if i["name"] == "Training frequency meets OAIC recommendation")
    assert item["passed"] is True


# --- Remediation Action Plan Render Test ---


def test_render_remediation_action_plan():
    """Remediation action plan template renders with proper context."""
    from app.generator import build_remediation_context

    from app.compliance_checker import calculate_compliance_score

    compliance = calculate_compliance_score(SAMPLE_DATA, set())
    ctx = build_remediation_context(SAMPLE_DATA, compliance)
    result = render_policy_text("remediation_action_plan", ctx)
    assert "Remediation" in result
    assert SAMPLE_DATA["business_name"] in result


# --- Template guard tests (None-safe) ---


def test_templates_render_with_none_lists():
    """Templates should not crash when list fields are None."""
    data = {
        **SAMPLE_DATA,
        "data_types_processed": None,
        "automated_decision_types": None,
    }
    ctx = build_template_context(data)
    # These templates iterate over the None fields — should not crash
    for tmpl in ("ai_acceptable_use", "privacy_policy", "ai_ethics_framework"):
        result = render_policy_text(tmpl, ctx)
        assert len(result) > 0


# --- LLM service sanitisation test ---


def test_llm_sanitise_field():
    """Sanitise function truncates and strips control chars."""
    from app.llm_service import _sanitise_field

    assert _sanitise_field("Normal text") == "Normal text"
    assert len(_sanitise_field("x" * 500)) == 200
    assert "\x00" not in _sanitise_field("bad\x00input")


# --- Board briefing and remediation via build_template_context (standard API path) ---


def test_board_briefing_renders_via_standard_context():
    """Board briefing should render without crash when policy_types comes from build_template_context default."""
    ctx = build_template_context(SAMPLE_DATA)
    # build_template_context now provides policy_types=[] by default
    assert "policy_types" in ctx
    result = render_policy_text("board_ai_briefing", ctx)
    assert "Board" in result
    assert SAMPLE_DATA["business_name"] in result


def test_board_briefing_shows_generated_status():
    """Board briefing with policy_types populated shows 'Generated' status."""
    from app.generator import build_board_briefing_context

    ctx = build_board_briefing_context(SAMPLE_DATA, {"ai_acceptable_use", "incident_response"})
    result = render_policy_text("board_ai_briefing", ctx)
    assert "Generated" in result


def test_remediation_renders_via_compliance_context():
    """Remediation action plan renders correctly with compliance-derived context."""
    from app.compliance_checker import calculate_compliance_score
    from app.generator import build_remediation_context

    compliance = calculate_compliance_score(SAMPLE_DATA, set())
    ctx = build_remediation_context(SAMPLE_DATA, compliance)
    result = render_policy_text("remediation_action_plan", ctx)
    assert "Remediation" in result
    assert SAMPLE_DATA["business_name"] in result
    assert ctx["score_percentage"] == compliance["score_percentage"]


# --- PDF generation tests ---


def test_save_policy_markdown_creates_file(tmp_path, monkeypatch):
    """save_policy_markdown writes file and returns correct hash."""
    from app.generator import save_policy_markdown
    import app.generator as gen_mod

    monkeypatch.setattr(gen_mod, "GENERATED_DIR", tmp_path)
    file_path, content_hash = save_policy_markdown("ai_acceptable_use", "# Test\nHello", 1)
    from pathlib import Path
    import hashlib

    fp = Path(file_path)
    assert fp.exists()
    assert fp.read_text(encoding="utf-8") == "# Test\nHello"
    assert content_hash == hashlib.sha256(b"# Test\nHello").hexdigest()


def test_save_policy_pdf_creates_file(tmp_path, monkeypatch):
    """save_policy_pdf produces a valid PDF file."""
    from app.generator import save_policy_pdf
    import app.generator as gen_mod

    monkeypatch.setattr(gen_mod, "GENERATED_DIR", tmp_path)
    md = "# Test Policy\n\n**Organisation:** Test Corp\n\n**Effective Date:** 2026-01-01\n\nSome content."
    file_path, content_hash = save_policy_pdf("ai_acceptable_use", md, 1)
    from pathlib import Path

    fp = Path(file_path)
    assert fp.exists()
    assert fp.suffix == ".pdf"
    # PDF files start with %PDF
    assert fp.read_bytes()[:5] == b"%PDF-"
    assert len(content_hash) == 64  # SHA-256 hex


def test_markdown_to_pdf_renders_tables(tmp_path):
    """markdown_to_pdf handles tables without crashing."""
    from app.generator import markdown_to_pdf

    md = "# Table Test\n\n| Col A | Col B |\n|---|---|\n| Val 1 | Val 2 |\n| Val 3 | Val 4 |\n\nEnd."
    output = tmp_path / "table_test.pdf"
    markdown_to_pdf(md, output)
    assert output.exists()
    assert output.read_bytes()[:5] == b"%PDF-"


def test_compliance_report_pdf_generates(tmp_path, monkeypatch):
    """generate_compliance_report_pdf produces a PDF from compliance results."""
    from app.compliance_checker import calculate_compliance_score
    from app.generator import generate_compliance_report_pdf
    import app.generator as gen_mod

    monkeypatch.setattr(gen_mod, "GENERATED_DIR", tmp_path)
    compliance = calculate_compliance_score(SAMPLE_DATA, set())
    file_path, content_hash = generate_compliance_report_pdf(SAMPLE_DATA, compliance, 99)
    from pathlib import Path

    fp = Path(file_path)
    assert fp.exists()
    assert fp.suffix == ".pdf"
    assert len(content_hash) == 64


def test_generate_policy_markdown_format(tmp_path, monkeypatch):
    """generate_policy() with output_format='markdown' produces a .md file."""
    from app.generator import generate_policy
    import app.generator as gen_mod

    monkeypatch.setattr(gen_mod, "GENERATED_DIR", tmp_path)
    file_path, content_hash = generate_policy("ai_acceptable_use", SAMPLE_DATA, 1, "markdown")
    from pathlib import Path

    fp = Path(file_path)
    assert fp.exists()
    assert fp.suffix == ".md"
    content = fp.read_text(encoding="utf-8")
    assert "Acme Pty Ltd" in content
    assert len(content_hash) == 64


def test_generate_policy_docx_fallback(tmp_path, monkeypatch):
    """generate_policy() with output_format='docx' falls back to PDF when no .docx template exists."""
    from app.generator import generate_policy
    import app.generator as gen_mod

    monkeypatch.setattr(gen_mod, "GENERATED_DIR", tmp_path)
    file_path, content_hash = generate_policy("ai_acceptable_use", SAMPLE_DATA, 1, "docx")
    from pathlib import Path

    fp = Path(file_path)
    assert fp.exists()
    # Falls back to PDF since no .docx template file exists
    assert fp.suffix == ".pdf"
    assert len(content_hash) == 64
