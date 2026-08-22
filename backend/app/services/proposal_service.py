import uuid
from typing import Sequence, Optional
from sqlalchemy.orm import Session
from app.database.models.agent_proposal import AgentProposal

def get_proposals(
    db: Session,
    limit: int = 50,
    offset: int = 0,
    agent_id: Optional[uuid.UUID] = None,
    merchant_id: Optional[uuid.UUID] = None,
    status: Optional[str] = None,
    event_type: Optional[str] = None
) -> Sequence[AgentProposal]:
    query = db.query(AgentProposal)
    if agent_id:
        query = query.filter(AgentProposal.agent_id == agent_id)
    if merchant_id:
        query = query.filter(AgentProposal.merchant_id == merchant_id)
    if status:
        query = query.filter(AgentProposal.status == status)
    if event_type:
        query = query.filter(AgentProposal.event_type == event_type)
        
    return query.order_by(AgentProposal.created_at.desc()).offset(offset).limit(limit).all()

def get_proposal_by_id(db: Session, proposal_id: uuid.UUID) -> Optional[AgentProposal]:
    return db.query(AgentProposal).filter(AgentProposal.id == proposal_id).first()
