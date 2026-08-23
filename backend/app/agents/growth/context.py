import uuid
from dataclasses import dataclass
from typing import List, Optional
from sqlalchemy.orm import Session
from app.database.models.customer import Customer
from app.database.models.merchant import Merchant
from app.database.models.transaction import Transaction

@dataclass
class GrowthContext:
    customer: Customer
    merchant: Merchant
    customer_history: List[Transaction]

def gather_growth_context(db: Session, merchant_id: uuid.UUID, customer_id: uuid.UUID) -> Optional[GrowthContext]:
    customer = db.query(Customer).filter(Customer.id == customer_id, Customer.merchant_id == merchant_id).first()
    if not customer:
        return None
    
    merchant = db.query(Merchant).filter(Merchant.id == merchant_id).first()
    if not merchant:
        return None
    
    customer_history = (
        db.query(Transaction)
        .filter(
            Transaction.customer_id == customer_id,
            Transaction.merchant_id == merchant_id
        )
        .order_by(Transaction.occurred_at.desc())
        .all()
    )
    
    return GrowthContext(
        customer=customer,
        merchant=merchant,
        customer_history=customer_history
    )
