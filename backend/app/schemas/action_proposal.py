import uuid
from datetime import datetime
from decimal import Decimal
from typing import Optional, Any
from pydantic import Field
from app.database.models.enums import ImpactLevel, ProposalStatus
from app.schemas.common import BaseSchema

class ActionProposalBase(BaseSchema):
    agent_id: uuid.UUID
    merchant_id: uuid.UUID
    event_type: str = Field(..., max_length=100)
    event_id: str = Field(..., max_length=255)
    action: str = Field(..., max_length=255)
    action_parameters: Optional[dict[str, Any]] = None
    confidence: Decimal = Field(..., ge=0, le=1)
    financial_impact: ImpactLevel
    customer_impact: ImpactLevel
    evidence: Any
    reason_summary: str = Field(..., max_length=1000)
    status: ProposalStatus = ProposalStatus.PENDING

class ActionProposalCreate(ActionProposalBase):
    pass

class ActionProposalResponse(ActionProposalBase):
    proposal_id: uuid.UUID = Field(..., validation_alias="id")
    created_at: datetime

from app.schemas.agent import AgentSummary
from app.schemas.merchant import MerchantSummary
from app.schemas.shield_decision import ShieldDecisionResponse

class ProposalDetailResponse(BaseSchema):
    proposal: ActionProposalResponse
    agent: AgentSummary
    merchant: MerchantSummary
    shield_decision: Optional[ShieldDecisionResponse] = None
