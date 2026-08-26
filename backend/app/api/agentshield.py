import uuid
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from app.database.session import get_db
from app.database.models.agent_proposal import AgentProposal
from app.agentshield.service import evaluate_proposal
from app.agentshield.schemas import EvaluateProposalResponse

router = APIRouter(prefix="/agentshield", tags=["AgentShield"])

@router.post(
    "/evaluate/{proposal_id}", 
    response_model=EvaluateProposalResponse, 
    status_code=status.HTTP_201_CREATED,
    summary="Evaluate an ActionProposal against AgentShield guardrails"
)
def evaluate_proposal_endpoint(proposal_id: uuid.UUID, db: Session = Depends(get_db)):
    """
    Load a proposal, run AgentShield checks, persist decisions, update statuses,
    generate audit logs, and return the aggregated Shield decision findings.
    """
    proposal = db.query(AgentProposal).filter(AgentProposal.id == proposal_id).first()
    if not proposal:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Proposal with ID {proposal_id} not found."
        )

    try:
        decision_db = evaluate_proposal(db, proposal_id)
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=str(e)
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Evaluation failed: {str(e)}"
        )

    return EvaluateProposalResponse(
        proposal_id=decision_db.proposal_id,
        decision=decision_db.decision,
        original_action=proposal.action,
        original_parameters=proposal.action_parameters,
        final_action=decision_db.final_action,
        final_action_parameters=decision_db.final_action_parameters,
        modifications=decision_db.modified_from,
        requires_human_review=decision_db.requires_human_review,
        reason_summary=decision_db.reason,
        checks=decision_db.checks
    )


# Part 12: Event processing orchestration structures
from pydantic import BaseModel, Field
from typing import Optional, List
from app.services.orchestration_service import process_event_orchestration

class EventProcessingRequest(BaseModel):
    event_type: str = Field(..., description="The type of event (e.g. TRANSACTION, PAYMENT_FAILURE, or GROWTH_OPPORTUNITY)")
    event_id: str = Field(..., description="The UUID of the transaction or customer context")

class ProposalSummary(BaseModel):
    proposal_id: str
    agent_key: str
    action: str
    status: str

class DecisionSummary(BaseModel):
    decision_id: str
    decision: str
    final_action: str
    reason: str

class EventProcessingResponse(BaseModel):
    event_id: str
    status: str
    executed_agents: List[str]
    proposals: List[ProposalSummary]
    final_decision: Optional[str] = None
    decision_id: Optional[str] = None
    decision_details: List[DecisionSummary]

@router.post(
    "/process-event", 
    response_model=EventProcessingResponse, 
    status_code=status.HTTP_201_CREATED,
    summary="Process an event end-to-end through multi-agent orchestration and AgentShield"
)
def process_event_endpoint(payload: EventProcessingRequest, db: Session = Depends(get_db)):
    """
    Receives an event, determines and runs all applicable agents, runs proposals through AgentShield,
    and returns resolved aggregated decision findings.
    """
    try:
        result = process_event_orchestration(db, payload.event_type, payload.event_id)
        return result
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=str(e)
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Event processing failed: {str(e)}"
        )
