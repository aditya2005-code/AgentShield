import uuid
from typing import Sequence, Optional
from sqlalchemy.orm import Session
from app.database.models.transaction import Transaction

def get_transactions(
    db: Session,
    limit: int = 50,
    offset: int = 0,
    merchant_id: Optional[uuid.UUID] = None,
    customer_id: Optional[uuid.UUID] = None,
    status: Optional[str] = None
) -> Sequence[Transaction]:
    query = db.query(Transaction)
    if merchant_id:
        query = query.filter(Transaction.merchant_id == merchant_id)
    if customer_id:
        query = query.filter(Transaction.customer_id == customer_id)
    if status:
        query = query.filter(Transaction.status == status)
    
    return query.order_by(Transaction.occurred_at.desc()).offset(offset).limit(limit).all()

def get_transaction_by_id(db: Session, transaction_id: uuid.UUID) -> Optional[Transaction]:
    return db.query(Transaction).filter(Transaction.id == transaction_id).first()
