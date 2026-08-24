import uuid
from typing import Optional, Any
from pydantic import BaseModel
from app.database.models.enums import ShieldDecisionType, ShieldCheckStatus

class CheckResultSchema(BaseModel):
    check: str
    status: ShieldCheckStatus
    policy_key: Optional[str] = None
    original_value: Optional[Any] = None
    allowed_value: Optional[Any] = None
    modification_required: bool = False
    details: Optional[dict[str, Any]] = None
    reason: Optional[str] = None

class EvaluateProposalResponse(BaseModel):
    proposal_id: uuid.UUID
    decision: ShieldDecisionType
    original_action: str
    original_parameters: Optional[dict[str, Any]] = None
    final_action: str
    final_action_parameters: Optional[dict[str, Any]] = None
    modifications: Optional[dict[str, Any]] = None
    requires_human_review: bool
    reason_summary: str
    checks: list[CheckResultSchema]
