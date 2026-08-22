import uuid
from typing import Sequence, Optional
from sqlalchemy.orm import Session
from app.database.models.audit_log import AuditLog

def get_audit_logs(
    db: Session,
    limit: int = 50,
    offset: int = 0,
    merchant_id: Optional[uuid.UUID] = None,
    agent_id: Optional[uuid.UUID] = None,
    proposal_id: Optional[uuid.UUID] = None,
    decision_id: Optional[uuid.UUID] = None,
    event_type: Optional[str] = None
) -> Sequence[AuditLog]:
    query = db.query(AuditLog)
    if merchant_id:
        query = query.filter(AuditLog.merchant_id == merchant_id)
    if agent_id:
        query = query.filter(AuditLog.agent_id == agent_id)
    if proposal_id:
        query = query.filter(AuditLog.proposal_id == proposal_id)
    if decision_id:
        query = query.filter(AuditLog.decision_id == decision_id)
    if event_type:
        query = query.filter(AuditLog.event_type == event_type)
        
    return query.order_by(AuditLog.created_at.desc()).offset(offset).limit(limit).all()
