import datetime

from sqlalchemy import JSON, Boolean, Column, DateTime, Float, ForeignKey, Index, Integer, String, Text

from app.database import Base


class Organisation(Base):
    __tablename__ = "organisations"

    id = Column(Integer, primary_key=True, index=True)
    business_name = Column(String, nullable=False)
    abn = Column(String, nullable=True)
    industry = Column(String, nullable=False)
    employee_count = Column(Integer, nullable=False)
    annual_revenue = Column(String, default="under_3m")
    revenue_exceeds_threshold = Column(Boolean, default=False)

    # AI usage
    ai_tools_in_use = Column(JSON, default=list)
    ai_tools_overseas = Column(JSON, default=list)
    shadow_ai_aware = Column(Boolean, default=False)
    shadow_ai_controls = Column(Boolean, default=False)
    customer_facing_ai = Column(Boolean, default=False)
    ai_generated_content_reviewed = Column(Boolean, default=False)

    # Automated decisions
    automated_decisions = Column(Boolean, default=False)
    automated_decision_types = Column(JSON, default=list)

    # Data
    data_types_processed = Column(JSON, default=list)
    trades_in_personal_info = Column(Boolean, default=False)

    # Vendor management
    vendor_dpa_in_place = Column(Boolean, default=False)
    pia_conducted = Column(Boolean, default=False)
    vendor_ai_clauses_reviewed = Column(Boolean, default=False)

    # Data governance
    has_data_retention_policy = Column(Boolean, default=False)
    data_retention_period = Column(String, default="no_defined_period")
    ai_outputs_logged = Column(Boolean, default=False)
    ai_access_restricted = Column(Boolean, default=False)
    has_privacy_policy = Column(Boolean, default=False)
    board_ai_awareness = Column(Boolean, default=False)
    consent_mechanism_exists = Column(Boolean, default=False)

    # Extended data & decisions
    ai_profiling_or_eligibility = Column(Boolean, default=False)
    bias_testing_conducted = Column(Boolean, default=False)
    ai_copyright_assessed = Column(Boolean, default=False)
    ai_in_marketing = Column(Boolean, default=False)
    human_review_available = Column(Boolean, default=False)

    # Extended vendor/compliance
    vendor_audit_rights = Column(Boolean, default=False)
    ndb_ai_process = Column(Boolean, default=False)
    ai_incident_register = Column(Boolean, default=False)
    essential_eight_applied = Column(Boolean, default=False)

    # Governance
    existing_it_policies = Column(Boolean, default=False)
    training_frequency = Column(String, default="annually")
    ai_governance_contact = Column(String, nullable=True)
    incident_response_tested = Column(Boolean, default=False)
    ai_disclosure_to_customers = Column(Boolean, default=False)
    ai_supply_chain_assessed = Column(Boolean, default=False)
    tranche2_aware = Column(Boolean, default=False)
    data_overseas_mapped = Column(Boolean, default=False)

    created_at = Column(DateTime, default=lambda: datetime.datetime.now(datetime.timezone.utc))


class PolicyDocument(Base):
    __tablename__ = "policy_documents"
    __table_args__ = (Index("ix_policy_documents_org_id", "org_id"),)

    id = Column(Integer, primary_key=True, index=True)
    org_id = Column(Integer, ForeignKey("organisations.id", ondelete="CASCADE"), nullable=False)
    template_type = Column(String, nullable=False)
    version = Column(Integer, default=1)
    generated_at = Column(DateTime, default=lambda: datetime.datetime.now(datetime.timezone.utc))
    file_path = Column(String, nullable=False)
    content_hash = Column(String, nullable=True)
    status = Column(String, default="generated")


class ComplianceSnapshot(Base):
    __tablename__ = "compliance_snapshots"
    __table_args__ = (Index("ix_compliance_snapshots_org_id", "org_id"),)

    id = Column(Integer, primary_key=True, index=True)
    org_id = Column(Integer, ForeignKey("organisations.id", ondelete="CASCADE"), nullable=False)
    industry = Column(String, nullable=False)
    score_percentage = Column(Float, nullable=False)
    risk_rating = Column(String, nullable=False)
    passed = Column(Integer, nullable=False)
    total = Column(Integer, nullable=False)
    penalty_exposure_total = Column(Float, default=0)
    created_at = Column(DateTime, default=lambda: datetime.datetime.now(datetime.timezone.utc))


class QuestionnaireProgress(Base):
    __tablename__ = "questionnaire_progress"

    id = Column(Integer, primary_key=True, index=True)
    session_key = Column(String, nullable=False, unique=True)
    step = Column(Integer, default=1)
    answers_json = Column(JSON, default=dict)
    updated_at = Column(
        DateTime,
        default=lambda: datetime.datetime.now(datetime.timezone.utc),
        onupdate=lambda: datetime.datetime.now(datetime.timezone.utc),
    )


class ComplianceEvidence(Base):
    __tablename__ = "compliance_evidence"
    __table_args__ = (Index("ix_compliance_evidence_org_id", "org_id"),)

    id = Column(Integer, primary_key=True, index=True)
    org_id = Column(Integer, ForeignKey("organisations.id", ondelete="CASCADE"), nullable=False)
    checklist_item_name = Column(String, nullable=False)  # maps to _ai6_checklist item "name"
    file_path = Column(String, nullable=False)
    file_name = Column(String, nullable=False)
    file_hash = Column(String, nullable=True)
    notes = Column(Text, nullable=True)
    uploaded_at = Column(DateTime, default=lambda: datetime.datetime.now(datetime.timezone.utc))


class RemediationAction(Base):
    __tablename__ = "remediation_actions"
    __table_args__ = (Index("ix_remediation_actions_org_id", "org_id"),)

    id = Column(Integer, primary_key=True, index=True)
    org_id = Column(Integer, ForeignKey("organisations.id", ondelete="CASCADE"), nullable=False)
    checklist_item_name = Column(String, nullable=False)
    action_description = Column(Text, nullable=False)
    severity = Column(String, nullable=False)  # critical, high, medium, low
    deadline = Column(DateTime, nullable=False)
    status = Column(String, default="pending")  # pending, in_progress, completed, overdue
    completed_at = Column(DateTime, nullable=True)
    notes = Column(Text, nullable=True)
    created_at = Column(DateTime, default=lambda: datetime.datetime.now(datetime.timezone.utc))


class AuditLog(Base):
    __tablename__ = "audit_log"
    __table_args__ = (
        Index("ix_audit_log_org_id", "org_id"),
        Index("ix_audit_log_event_type", "event_type"),
    )

    id = Column(Integer, primary_key=True, index=True)
    event_type = Column(String, nullable=False)
    timestamp = Column(DateTime, default=lambda: datetime.datetime.now(datetime.timezone.utc))
    user_id = Column(String, nullable=True)
    org_id = Column(Integer, nullable=True)
    metadata_json = Column(JSON, default=dict)
    content_hash = Column(String, nullable=True)
    details = Column(Text, nullable=True)


def org_to_dict(org: Organisation) -> dict:
    """Convert an Organisation ORM instance to a plain dict for compliance scoring."""
    return {
        "business_name": org.business_name,
        "abn": org.abn,
        "industry": org.industry,
        "employee_count": org.employee_count,
        "annual_revenue": org.annual_revenue,
        "revenue_exceeds_threshold": org.revenue_exceeds_threshold,
        "ai_tools_in_use": org.ai_tools_in_use or [],
        "ai_tools_overseas": org.ai_tools_overseas or [],
        "shadow_ai_aware": org.shadow_ai_aware,
        "shadow_ai_controls": org.shadow_ai_controls,
        "customer_facing_ai": org.customer_facing_ai,
        "ai_generated_content_reviewed": org.ai_generated_content_reviewed,
        "ai_access_restricted": org.ai_access_restricted,
        "ai_outputs_logged": org.ai_outputs_logged,
        "automated_decisions": org.automated_decisions,
        "automated_decision_types": org.automated_decision_types or [],
        "data_types_processed": org.data_types_processed or [],
        "trades_in_personal_info": org.trades_in_personal_info,
        "has_data_retention_policy": org.has_data_retention_policy,
        "data_retention_period": org.data_retention_period,
        "consent_mechanism_exists": org.consent_mechanism_exists,
        "vendor_dpa_in_place": org.vendor_dpa_in_place,
        "pia_conducted": org.pia_conducted,
        "has_privacy_policy": org.has_privacy_policy,
        "vendor_ai_clauses_reviewed": org.vendor_ai_clauses_reviewed,
        "existing_it_policies": org.existing_it_policies,
        "incident_response_tested": org.incident_response_tested,
        "board_ai_awareness": org.board_ai_awareness,
        "training_frequency": org.training_frequency,
        "ai_governance_contact": org.ai_governance_contact,
        "ai_profiling_or_eligibility": org.ai_profiling_or_eligibility,
        "bias_testing_conducted": org.bias_testing_conducted,
        "ai_copyright_assessed": org.ai_copyright_assessed,
        "ai_in_marketing": org.ai_in_marketing,
        "human_review_available": org.human_review_available,
        "vendor_audit_rights": org.vendor_audit_rights,
        "ndb_ai_process": org.ndb_ai_process,
        "ai_incident_register": org.ai_incident_register,
        "essential_eight_applied": org.essential_eight_applied,
        "ai_disclosure_to_customers": org.ai_disclosure_to_customers,
        "ai_supply_chain_assessed": org.ai_supply_chain_assessed,
        "tranche2_aware": org.tranche2_aware,
        "data_overseas_mapped": org.data_overseas_mapped,
    }
