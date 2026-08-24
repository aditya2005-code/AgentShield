from dataclasses import dataclass
from typing import Optional, List
from sqlalchemy.orm import Session
from app.database.models.agent_proposal import AgentProposal
from app.database.models.agent import Agent
from app.database.models.merchant import Merchant
from app.database.models.merchant_policy import MerchantPolicy
from app.database.models.agent_permission import AgentPermission
from app.database.models.customer import Customer
from app.database.models.transaction import Transaction

@dataclass
class EvaluationContext:
    proposal: AgentProposal
    agent: Agent
    merchant: Merchant
    policies: List[MerchantPolicy]
    permission: Optional[AgentPermission]
    customer: Optional[Customer] = None
    transaction: Optional[Transaction] = None
    retry_count: int = 0
    db: Session = None
