from typing import Any, Optional
from pydantic import BaseModel
from app.schemas.agent import AgentResponse
from app.schemas.action_proposal import ActionProposalResponse
from app.schemas.merchant_policy import MerchantPolicyResponse
from app.schemas.shield_decision import ShieldDecisionResponse
from app.schemas.audit_log import AuditLogResponse

class DemoScenarioResponse(BaseModel):
    event: dict[str, Any]
    agent: AgentResponse
    proposal: ActionProposalResponse
    merchant_policies: list[MerchantPolicyResponse]
    shield_decision: ShieldDecisionResponse
    audit_logs: list[AuditLogResponse]

class DemoScenarioListResponse(BaseModel):
    scenarios: list[str]
