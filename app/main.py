from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from pathlib import Path
from typing import cast

from fastapi import Depends, FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from sqlalchemy.orm import Session

from app.audit import get_audit_logs, log_event
from app.compliance_checker import calculate_compliance_score, get_industry_benchmarks, save_compliance_snapshot
from app.config import GENERATED_DIR
from app.database import get_db, init_db
from app.generator import TEMPLATE_TYPES, build_remediation_context, generate_compliance_report_pdf, generate_policy
from app.models import Organisation, PolicyDocument
from app.questionnaire import QuestionnaireResponse, get_questions


@asynccontextmanager
async def lifespan(_app: FastAPI) -> AsyncIterator[None]:
    init_db()
    try:
        from app.rag_service import rag_service

        rag_service.initialize()
    except Exception as exc:
        import logging

        logging.getLogger(__name__).warning("RAG service initialization failed (non-critical): %s", exc)
    yield


app = FastAPI(title="AI Compliance Policy Generator", version="2.0.0", lifespan=lifespan)

from app.config import settings as _settings

app.add_middleware(
    CORSMiddleware,
    allow_origins=[o.strip() for o in _settings.cors_origins.split(",") if o.strip()],
    allow_credentials=True,
    allow_methods=["GET", "POST", "OPTIONS"],
    allow_headers=["Content-Type"],
)


# --- Questionnaire ---


@app.get("/api/questions")
def list_questions():
    return get_questions()


@app.post("/api/questionnaire")
def submit_questionnaire(response: QuestionnaireResponse, db: Session = Depends(get_db)):
    org = Organisation(
        business_name=response.business_name,
        abn=response.abn,
        industry=response.industry.value,
        employee_count=response.employee_count,
        annual_revenue=response.annual_revenue.value,
        revenue_exceeds_threshold=response.revenue_exceeds_threshold,
        ai_tools_in_use=response.ai_tools_in_use,
        ai_tools_overseas=response.ai_tools_overseas,
        shadow_ai_aware=response.shadow_ai_aware,
        shadow_ai_controls=response.shadow_ai_controls,
        customer_facing_ai=response.customer_facing_ai,
        ai_generated_content_reviewed=response.ai_generated_content_reviewed,
        ai_access_restricted=response.ai_access_restricted,
        ai_outputs_logged=response.ai_outputs_logged,
        automated_decisions=response.automated_decisions,
        automated_decision_types=response.automated_decision_types,
        data_types_processed=response.data_types_processed,
        trades_in_personal_info=response.trades_in_personal_info,
        has_data_retention_policy=response.has_data_retention_policy,
        data_retention_period=response.data_retention_period.value,
        consent_mechanism_exists=response.consent_mechanism_exists,
        vendor_dpa_in_place=response.vendor_dpa_in_place,
        pia_conducted=response.pia_conducted,
        has_privacy_policy=response.has_privacy_policy,
        vendor_ai_clauses_reviewed=response.vendor_ai_clauses_reviewed,
        existing_it_policies=response.existing_it_policies,
        incident_response_tested=response.incident_response_tested,
        board_ai_awareness=response.board_ai_awareness,
        training_frequency=response.training_frequency.value,
        ai_governance_contact=response.ai_governance_contact,
        ai_profiling_or_eligibility=response.ai_profiling_or_eligibility,
        bias_testing_conducted=response.bias_testing_conducted,
        ai_copyright_assessed=response.ai_copyright_assessed,
        ai_in_marketing=response.ai_in_marketing,
        human_review_available=response.human_review_available,
        vendor_audit_rights=response.vendor_audit_rights,
        ndb_ai_process=response.ndb_ai_process,
        ai_incident_register=response.ai_incident_register,
        essential_eight_applied=response.essential_eight_applied,
        ai_disclosure_to_customers=response.ai_disclosure_to_customers,
        ai_supply_chain_assessed=response.ai_supply_chain_assessed,
        tranche2_aware=response.tranche2_aware,
        data_overseas_mapped=response.data_overseas_mapped,
    )
    db.add(org)
    db.commit()
    db.refresh(org)

    org_id = cast("int", org.id)
    log_event(
        db,
        event_type="questionnaire_submitted",
        org_id=org_id,
        metadata={"industry": org.industry, "employee_count": org.employee_count},
    )

    return {"org_id": org_id, "message": "Questionnaire submitted successfully"}


def _org_to_dict(org: Organisation) -> dict:
    from app.models import org_to_dict

    return org_to_dict(org)


@app.get("/api/organisation/{org_id}")
def get_organisation(org_id: int, db: Session = Depends(get_db)):
    org = db.query(Organisation).filter(Organisation.id == org_id).first()
    if not org:
        raise HTTPException(status_code=404, detail=f"Organisation {org_id} not found")
    return _org_to_dict(org)


# --- Policy Generation ---


@app.post("/api/generate/{template_type}")
def generate(
    template_type: str,
    org_id: int,
    output_format: str = "pdf",
    enhance_with_llm: bool = False,
    db: Session = Depends(get_db),
):
    if template_type not in TEMPLATE_TYPES:
        raise HTTPException(
            status_code=400,
            detail=f"Invalid template type. Choose from: {list(TEMPLATE_TYPES.keys())}",
        )

    org = db.query(Organisation).filter(Organisation.id == org_id).first()
    if not org:
        raise HTTPException(status_code=404, detail=f"Organisation {org_id} not found")

    questionnaire_data = _org_to_dict(org)

    oid = cast("int", org.id)

    # Templates that need specialised context builders
    existing_policies = db.query(PolicyDocument).filter(PolicyDocument.org_id == oid).all()
    policy_types_set = {p.template_type for p in existing_policies}

    if template_type == "board_ai_briefing":
        from app.generator import build_board_briefing_context

        ctx = build_board_briefing_context(questionnaire_data, policy_types_set)
        from app.generator import render_policy_text, save_policy_pdf, save_policy_markdown

        content = render_policy_text(template_type, ctx)
        if output_format == "pdf":
            file_path, content_hash = save_policy_pdf(template_type, content, oid)
        else:
            file_path, content_hash = save_policy_markdown(template_type, content, oid)
    elif template_type == "remediation_action_plan":
        compliance_result = calculate_compliance_score(questionnaire_data, policy_types_set)
        ctx = build_remediation_context(questionnaire_data, compliance_result)
        from app.generator import render_policy_text, save_policy_pdf, save_policy_markdown

        content = render_policy_text(template_type, ctx)
        if output_format == "pdf":
            file_path, content_hash = save_policy_pdf(template_type, content, oid)
        else:
            file_path, content_hash = save_policy_markdown(template_type, content, oid)
    else:
        file_path, content_hash = generate_policy(
            template_type,
            questionnaire_data,
            oid,
            output_format,
            enhance_with_llm=enhance_with_llm,
        )

    existing = (
        db.query(PolicyDocument)
        .filter(
            PolicyDocument.org_id == oid,
            PolicyDocument.template_type == template_type,
        )
        .count()
    )

    policy = PolicyDocument(
        org_id=oid,
        template_type=template_type,
        version=existing + 1,
        file_path=file_path,
        content_hash=content_hash,
        status="generated",
    )
    db.add(policy)
    try:
        db.commit()
        db.refresh(policy)
    except Exception:
        db.rollback()
        # Clean up orphaned file
        _fp = Path(file_path)
        if _fp.exists():
            _fp.unlink(missing_ok=True)
        raise

    log_event(
        db,
        event_type="policy_generated",
        org_id=oid,
        metadata={
            "template_type": template_type,
            "version": policy.version,
            "format": output_format,
        },
        content_hash=content_hash,
    )

    return {
        "policy_id": policy.id,
        "file_path": file_path,
        "version": policy.version,
        "content_hash": content_hash,
    }


# --- Policies ---


@app.get("/api/policies/{org_id}")
def list_policies(org_id: int, db: Session = Depends(get_db)):
    policies = (
        db.query(PolicyDocument)
        .filter(PolicyDocument.org_id == org_id)
        .order_by(PolicyDocument.generated_at.desc())
        .all()
    )
    return [
        {
            "id": p.id,
            "org_id": p.org_id,
            "template_type": p.template_type,
            "version": p.version,
            "file_path": p.file_path,
            "content_hash": p.content_hash,
            "status": p.status,
            "generated_at": p.generated_at.isoformat() if p.generated_at else None,
        }
        for p in policies
    ]


@app.get("/api/download/{policy_id}")
def download_policy(policy_id: int, db: Session = Depends(get_db)):
    policy = db.query(PolicyDocument).filter(PolicyDocument.id == policy_id).first()
    if not policy:
        raise HTTPException(status_code=404, detail=f"Policy {policy_id} not found")

    file_path = Path(policy.file_path).resolve()
    if not file_path.is_relative_to(GENERATED_DIR.resolve()):
        raise HTTPException(status_code=403, detail="Access denied")
    if not file_path.exists():
        raise HTTPException(status_code=404, detail="File not found on disk")

    log_event(
        db,
        event_type="policy_downloaded",
        org_id=cast("int", policy.org_id),
        metadata={"policy_id": policy.id, "template_type": policy.template_type},
        content_hash=cast("str", policy.content_hash),
    )

    mime_map = {
        ".pdf": "application/pdf",
        ".docx": "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
        ".md": "text/markdown",
    }
    media_type = mime_map.get(file_path.suffix, "application/octet-stream")
    return FileResponse(path=str(file_path), filename=file_path.name, media_type=media_type)


# --- Benchmarking ---


@app.get("/api/benchmarks/{industry}")
def get_benchmarks(industry: str, org_score: float = 0, db: Session = Depends(get_db)):
    return get_industry_benchmarks(db, industry, org_score)


# --- Compliance Report & Remediation ---


@app.post("/api/generate-report/{org_id}")
def generate_report(org_id: int, db: Session = Depends(get_db)):
    org = db.query(Organisation).filter(Organisation.id == org_id).first()
    if not org:
        raise HTTPException(status_code=404, detail=f"Organisation {org_id} not found")

    org_data = _org_to_dict(org)
    policies = db.query(PolicyDocument).filter(PolicyDocument.org_id == org_id).all()
    policy_types = cast("set[str]", {p.template_type for p in policies})
    compliance_result = calculate_compliance_score(org_data, policy_types)

    save_compliance_snapshot(db, org_id, org_data["industry"], compliance_result)

    file_path, content_hash = generate_compliance_report_pdf(org_data, compliance_result, org_id)

    existing = (
        db.query(PolicyDocument)
        .filter(PolicyDocument.org_id == org_id, PolicyDocument.template_type == "compliance_report")
        .count()
    )

    policy = PolicyDocument(
        org_id=org_id,
        template_type="compliance_report",
        version=existing + 1,
        file_path=file_path,
        content_hash=content_hash,
        status="generated",
    )
    db.add(policy)
    try:
        db.commit()
        db.refresh(policy)
    except Exception:
        db.rollback()
        _fp = Path(file_path)
        if _fp.exists():
            _fp.unlink(missing_ok=True)
        raise

    log_event(
        db,
        event_type="policy_generated",
        org_id=org_id,
        metadata={"template_type": "compliance_report", "version": policy.version, "format": "pdf"},
        content_hash=content_hash,
    )

    return {"policy_id": policy.id, "file_path": file_path, "content_hash": content_hash}


@app.post("/api/generate-remediation/{org_id}")
def generate_remediation(org_id: int, db: Session = Depends(get_db)):
    org = db.query(Organisation).filter(Organisation.id == org_id).first()
    if not org:
        raise HTTPException(status_code=404, detail=f"Organisation {org_id} not found")

    org_data = _org_to_dict(org)
    policies = db.query(PolicyDocument).filter(PolicyDocument.org_id == org_id).all()
    policy_types = cast("set[str]", {p.template_type for p in policies})
    compliance_result = calculate_compliance_score(org_data, policy_types)

    context = build_remediation_context(org_data, compliance_result)
    from app.generator import render_policy_text, save_policy_pdf

    content = render_policy_text("remediation_action_plan", context)
    file_path, content_hash = save_policy_pdf("remediation_action_plan", content, org_id)

    existing = (
        db.query(PolicyDocument)
        .filter(PolicyDocument.org_id == org_id, PolicyDocument.template_type == "remediation_action_plan")
        .count()
    )

    policy = PolicyDocument(
        org_id=org_id,
        template_type="remediation_action_plan",
        version=existing + 1,
        file_path=file_path,
        content_hash=content_hash,
        status="generated",
    )
    db.add(policy)
    try:
        db.commit()
        db.refresh(policy)
    except Exception:
        db.rollback()
        _fp = Path(file_path)
        if _fp.exists():
            _fp.unlink(missing_ok=True)
        raise

    log_event(
        db,
        event_type="policy_generated",
        org_id=org_id,
        metadata={"template_type": "remediation_action_plan", "version": policy.version, "format": "pdf"},
        content_hash=content_hash,
    )

    return {"policy_id": policy.id, "file_path": file_path, "content_hash": content_hash}


# --- Audit Log ---


@app.get("/api/audit-log")
def list_audit_logs(
    org_id: int | None = None,
    event_type: str | None = None,
    limit: int = 100,
    db: Session = Depends(get_db),
):
    logs = get_audit_logs(db, org_id=org_id, event_type=event_type, limit=min(limit, 500))
    return [
        {
            "id": log.id,
            "event_type": log.event_type,
            "timestamp": log.timestamp.isoformat() if log.timestamp else None,
            "user_id": log.user_id,
            "org_id": log.org_id,
            "metadata": log.metadata_json,
            "content_hash": log.content_hash,
            "details": log.details,
        }
        for log in logs
    ]
