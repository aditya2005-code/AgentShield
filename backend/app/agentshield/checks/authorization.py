from app.agentshield.checks.base import BaseShieldCheck
from app.agentshield.context import EvaluationContext
from app.agentshield.schemas import CheckResultSchema
from app.database.models.enums import ShieldCheckStatus, AgentType

class AuthorizationCheck(BaseShieldCheck):
    @property
    def check_name(self) -> str:
        return "authorization"

    def run(self, context: EvaluationContext) -> CheckResultSchema:
        proposal = context.proposal
        agent = context.agent
        permission = context.permission

        # 1. Define allowed actions by agent type — PRIMARY authority
        allowed_scopes = {
            AgentType.FRAUD: {"ALLOW_TRANSACTION", "STEP_UP_VERIFICATION", "BLOCK_TRANSACTION", "ESCALATE_TO_REVIEW"},
            AgentType.RECOVERY: {"WAIT_AND_RETRY", "REQUEST_NEW_PAYMENT_METHOD", "ESCALATE_TO_SUPPORT", "DO_NOT_RETRY"},
            AgentType.GROWTH: {"SEND_PROMOTION", "APPLY_DISCOUNT", "OFFER_UPSELL", "NO_ACTION"}
        }

        agent_scope = allowed_scopes.get(agent.agent_type, set())

        # Reject immediately if action is outside the hardcoded allowed scope
        if proposal.action not in agent_scope:
            return CheckResultSchema(
                check=self.check_name,
                status=ShieldCheckStatus.FAILED,
                reason=f"Action '{proposal.action}' is outside the authorized scope for agent type {agent.agent_type.value}.",
                details={"agent_type": agent.agent_type.value, "proposed_action": proposal.action}
            )

        # 2. Consult DB permission row only if it exists — used for explicit operator overrides only.
        # A missing permission row is NOT a failure; the scope check above is sufficient.
        if permission is not None:
            if not permission.is_allowed:
                return CheckResultSchema(
                    check=self.check_name,
                    status=ShieldCheckStatus.FAILED,
                    reason=f"Agent permission explicitly disabled in database for action '{proposal.action}'.",
                    details={"agent_id": str(agent.id), "action": proposal.action, "is_allowed": False}
                )

            if permission.requires_human_review:
                return CheckResultSchema(
                    check=self.check_name,
                    status=ShieldCheckStatus.WARNING,
                    reason=f"Agent permission configuration requires human review for action '{proposal.action}'.",
                    details={"agent_id": str(agent.id), "action": proposal.action, "requires_human_review": True}
                )

        return CheckResultSchema(
            check=self.check_name,
            status=ShieldCheckStatus.PASSED,
            reason=f"Agent {agent.name} is authorized to propose action '{proposal.action}'.",
            details={"agent_id": str(agent.id), "action": proposal.action}
        )
