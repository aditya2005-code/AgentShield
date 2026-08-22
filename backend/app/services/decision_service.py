import uuid
from typing import Sequence, Optional
from sqlalchemy.orm import Session
from app.database.models.shield_decision import ShieldDecision

def get_decisions(
    db: Session,
    limit: int = 50,
    offset: int = 0,
    decision: Optional[str] = None,
    requires_human_review: Optional[bool] = None
) -> Sequence[ShieldDecision]:
    query = db.query(ShieldDecision)
    if decision:
        query = query.filter(ShieldDecision.decision == decision)
    if requires_human_review is not None:
        query = query.filter(ShieldDecision.requires_human_review == requires_human_review)
        
    return query.order_by(ShieldDecision.created_at.desc()).offset(offset).limit(limit).all()

def get_decision_by_id(db: Session, decision_id: uuid.UUID) -> Optional[ShieldDecision]:
    return db.query(ShieldDecision).filter(ShieldDecision.id == decision_id).first()
