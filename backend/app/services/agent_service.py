import uuid
from typing import Sequence, Optional
from sqlalchemy.orm import Session
from app.database.models.agent import Agent

def get_agents(db: Session) -> Sequence[Agent]:
    return db.query(Agent).all()

def get_agent_by_id(db: Session, agent_id: uuid.UUID) -> Optional[Agent]:
    return db.query(Agent).filter(Agent.id == agent_id).first()
