import datetime

from sqlalchemy.orm import Session

from app.models import AuditLog


def log_event(
    db: Session,
    event_type: str,
    org_id: int | None = None,
    user_id: str | None = None,
    metadata: dict | None = None,
    content_hash: str | None = None,
    details: str | None = None,
) -> AuditLog:
    entry = AuditLog(
        event_type=event_type,
        timestamp=datetime.datetime.now(datetime.timezone.utc),
        user_id=user_id,
        org_id=org_id,
        metadata_json=metadata or {},
        content_hash=content_hash,
        details=details,
    )
    db.add(entry)
    try:
        db.commit()
        db.refresh(entry)
    except Exception:
        db.rollback()
        raise
    return entry


def get_audit_logs(
    db: Session,
    org_id: int | None = None,
    event_type: str | None = None,
    limit: int = 100,
) -> list[AuditLog]:
    query = db.query(AuditLog)
    if org_id is not None:
        query = query.filter(AuditLog.org_id == org_id)
    if event_type is not None:
        query = query.filter(AuditLog.event_type == event_type)
    return query.order_by(AuditLog.timestamp.desc()).limit(limit).all()
