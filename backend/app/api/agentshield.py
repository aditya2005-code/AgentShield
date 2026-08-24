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
