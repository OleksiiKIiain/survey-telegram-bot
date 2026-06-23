from sqlalchemy.orm import Session

from app.models.audit_log import AuditLog


def log_action(db: Session, admin_id: int | None, action: str, entity_type: str, entity_id: int | None = None, details: dict | None = None) -> None:
    db.add(AuditLog(admin_id=admin_id, action=action, entity_type=entity_type, entity_id=entity_id, details=details or {}))
