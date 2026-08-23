import uuid
from dataclasses import dataclass
from typing import List, Optional
from sqlalchemy.orm import Session
from app.database.models.transaction import Transaction
from app.database.models.customer import Customer
from app.database.models.merchant import Merchant
from app.database.models.agent_proposal import AgentProposal

@dataclass
class RecoveryContext:
    transaction: Transaction
    customer: Customer
    merchant: Merchant
    customer_history: List[Transaction]
    previous_proposals: List[AgentProposal]

def gather_recovery_context(db: Session, transaction_id: uuid.UUID) -> Optional[RecoveryContext]:
    transaction = db.query(Transaction).filter(Transaction.id == transaction_id).first()
    if not transaction:
        return None
    
    customer = db.query(Customer).filter(Customer.id == transaction.customer_id).first()
    merchant = db.query(Merchant).filter(Merchant.id == transaction.merchant_id).first()
    
    customer_history = (
        db.query(Transaction)
        .filter(Transaction.customer_id == transaction.customer_id, Transaction.id != transaction.id)
        .order_by(Transaction.occurred_at.desc())
        .all()
    )
    
    previous_proposals = (
        db.query(AgentProposal)
        .filter(
            AgentProposal.event_id == str(transaction_id),
            AgentProposal.event_type.in_(["PAYMENT_FAILURE", "TRANSACTION"])
        )
        .order_by(AgentProposal.created_at.desc())
        .all()
    )
    
    return RecoveryContext(
        transaction=transaction,
        customer=customer,
        merchant=merchant,
        customer_history=customer_history,
        previous_proposals=previous_proposals
    )
