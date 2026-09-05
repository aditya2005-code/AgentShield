import uuid
from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session
from app.database.session import get_db
from app.schemas.shield_decision import ShieldDecisionResponse, ShieldDecisionDetailResponse
from app.services import decision_service

router = APIRouter(prefix="/decisions", tags=["Shield Decisions"])

@router.get("", response_model=List[ShieldDecisionResponse], summary="Retrieve list of shield decisions")
def read_decisions(
    decision: Optional[str] = Query(None, description="Filter by decision type (APPROVE, MODIFY, ESCALATE, REJECT)"),
    requires_human_review: Optional[bool] = Query(None, description="Filter by review flag status"),
    limit: int = Query(50, ge=1, le=100, description="Number of records to return"),
    offset: int = Query(0, ge=0, description="Offset for pagination"),
    db: Session = Depends(get_db)
):
    """
    Fetch a list of AgentShield decisions, sorted by newest first, with support for filtering and pagination.
    """
    return decision_service.get_decisions(
        db, limit=limit, offset=offset, decision=decision, requires_human_review=requires_human_review
    )

@router.get("/{decision_id}", response_model=ShieldDecisionDetailResponse, summary="Retrieve a single decision with details")
def read_decision(decision_id: uuid.UUID, db: Session = Depends(get_db)):
    """
    Fetch complete details of a shield decision including the associated proposal summary and proposing agent details.
    """
    decision = decision_service.get_decision_by_id(db, decision_id)
    if not decision:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Shield decision with ID {decision_id} not found"
        )
        
    return {
        "id": decision.id,
        "decision_id": decision.id,
        "proposal_id": decision.proposal_id,
        "decision": decision.decision,
        "final_action": decision.final_action,
        "final_action_parameters": decision.final_action_parameters,
        "modified_from": decision.modified_from,
        "checks": decision.checks,
        "reason": decision.reason,
        "requires_human_review": decision.requires_human_review,
        "created_at": decision.created_at,
        "proposal": decision.proposal,
        "agent": decision.proposal.agent if decision.proposal else None
    }
