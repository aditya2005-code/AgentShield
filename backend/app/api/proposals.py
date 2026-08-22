import uuid
from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session
from app.database.session import get_db
from app.schemas.action_proposal import ActionProposalResponse, ProposalDetailResponse
from app.services import proposal_service

router = APIRouter(prefix="/proposals", tags=["Agent Proposals"])

@router.get("", response_model=List[ActionProposalResponse], summary="Retrieve list of agent proposals")
def read_proposals(
    agent_id: Optional[uuid.UUID] = Query(None, description="Filter by agent UUID"),
    merchant_id: Optional[uuid.UUID] = Query(None, description="Filter by merchant UUID"),
    status: Optional[str] = Query(None, description="Filter by proposal status (PENDING, REVIEWED, EXECUTED, REJECTED)"),
    event_type: Optional[str] = Query(None, description="Filter by source event type"),
    limit: int = Query(50, ge=1, le=100, description="Number of records to return"),
    offset: int = Query(0, ge=0, description="Offset for pagination"),
    db: Session = Depends(get_db)
):
    """
    Fetch a list of agent action proposals, sorted by newest first, with support for filtering and pagination.
    """
    return proposal_service.get_proposals(
        db, limit=limit, offset=offset, agent_id=agent_id, merchant_id=merchant_id, status=status, event_type=event_type
    )

@router.get("/{proposal_id}", response_model=ProposalDetailResponse, summary="Retrieve a single proposal with details")
def read_proposal(proposal_id: uuid.UUID, db: Session = Depends(get_db)):
    """
    Fetch complete context of a single proposal including agent summary, merchant summary, and associated shield decision.
    """
    proposal = proposal_service.get_proposal_by_id(db, proposal_id)
    if not proposal:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Proposal with ID {proposal_id} not found"
        )
        
    return {
        "proposal": proposal,
        "agent": proposal.agent,
        "merchant": proposal.merchant,
        "shield_decision": proposal.shield_decision
    }
