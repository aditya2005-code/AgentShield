import uuid
from typing import List, Optional
from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session
from app.database.session import get_db
from app.schemas.audit_log import AuditLogResponse
from app.services import audit_log_service

router = APIRouter(prefix="/audit-logs", tags=["Audit Logs"])

@router.get("", response_model=List[AuditLogResponse], summary="Retrieve list of audit logs")
def read_audit_logs(
    merchant_id: Optional[uuid.UUID] = Query(None, description="Filter by merchant UUID"),
    agent_id: Optional[uuid.UUID] = Query(None, description="Filter by agent UUID"),
    proposal_id: Optional[uuid.UUID] = Query(None, description="Filter by proposal UUID"),
    decision_id: Optional[uuid.UUID] = Query(None, description="Filter by decision UUID"),
    event_type: Optional[str] = Query(None, description="Filter by audit event type (AGENT_PROPOSAL_CREATED, SHIELD_DECISION_CREATED, ACTION_EXECUTED)"),
    limit: int = Query(50, ge=1, le=100, description="Number of records to return"),
    offset: int = Query(0, ge=0, description="Offset for pagination"),
    db: Session = Depends(get_db)
):
    """
    Fetch a list of system audit logs, sorted by newest first, with support for filtering and pagination.
    """
    return audit_log_service.get_audit_logs(
        db, limit=limit, offset=offset, merchant_id=merchant_id, agent_id=agent_id,
        proposal_id=proposal_id, decision_id=decision_id, event_type=event_type
    )
