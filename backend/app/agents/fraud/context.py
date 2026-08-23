import uuid
from dataclasses import dataclass
from typing import List, Optional
from sqlalchemy.orm import Session
from app.database.models.transaction import Transaction
from app.database.models.customer import Customer
from app.database.models.merchant import Merchant
from app.database.models.device import Device
from app.database.models.agent_proposal import AgentProposal

@dataclass
class FraudContext:
    transaction: Transaction
    customer: Customer
    merchant: Merchant
    device: Optional[Device]
    customer_history: List[Transaction]
    recent_proposals: List[AgentProposal]

def gather_fraud_context(db: Session, transaction_id: uuid.UUID) -> Optional[FraudContext]:
    transaction = db.query(Transaction).filter(Transaction.id == transaction_id).first()
    if not transaction:
        return None
    
    customer = db.query(Customer).filter(Customer.id == transaction.customer_id).first()
    merchant = db.query(Merchant).filter(Merchant.id == transaction.merchant_id).first()
    
    device = None
    if transaction.device_id:
        device = db.query(Device).filter(Device.id == transaction.device_id).first()
        
    customer_history = (
        db.query(Transaction)
        .filter(Transaction.customer_id == transaction.customer_id, Transaction.id != transaction.id)
        .order_by(Transaction.occurred_at.desc())
        .all()
    )
    
    recent_proposals = (
        db.query(AgentProposal)
        .filter(AgentProposal.merchant_id == transaction.merchant_id)
        .order_by(AgentProposal.created_at.desc())
        .limit(10)
        .all()
    )
    
    return FraudContext(
        transaction=transaction,
        customer=customer,
        merchant=merchant,
        device=device,
        customer_history=customer_history,
        recent_proposals=recent_proposals
    )
