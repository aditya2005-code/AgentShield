import uuid
from datetime import datetime
from typing import Optional, Any
from pydantic import Field
from app.database.models.enums import ShieldDecisionType
from app.schemas.common import BaseSchema

class ShieldDecisionBase(BaseSchema):
    proposal_id: uuid.UUID
    decision: ShieldDecisionType
    final_action: str = Field(..., max_length=255)
    final_action_parameters: Optional[dict[str, Any]] = None
    modified_from: Optional[dict[str, Any]] = None
    checks: list[dict[str, Any]]
    reason: str = Field(..., max_length=1000)
    requires_human_review: bool = False

class ShieldDecisionCreate(ShieldDecisionBase):
    pass

class ShieldDecisionResponse(ShieldDecisionBase):
    decision_id: uuid.UUID = Field(..., validation_alias="id")
    created_at: datetime

from app.schemas.agent import AgentSummary

class ProposalSummary(BaseSchema):
    proposal_id: uuid.UUID = Field(..., validation_alias="id")
    event_type: str
    event_id: str
    action: str
    confidence: float
    status: str

class ShieldDecisionDetailResponse(ShieldDecisionResponse):
    proposal: ProposalSummary
    agent: Optional[AgentSummary] = None
