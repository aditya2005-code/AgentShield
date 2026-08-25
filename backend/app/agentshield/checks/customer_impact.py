from app.agentshield.checks.base import BaseShieldCheck
from app.agentshield.context import EvaluationContext
from app.agentshield.schemas import CheckResultSchema
from app.database.models.enums import ShieldCheckStatus, ImpactLevel

class CustomerImpactCheck(BaseShieldCheck):
    @property
    def check_name(self) -> str:
        return "customer_impact"

    def run(self, context: EvaluationContext) -> CheckResultSchema:
        proposal = context.proposal

        # 1. Proposal customer impact level checks
        if proposal.customer_impact == ImpactLevel.CRITICAL:
            return CheckResultSchema(
                check=self.check_name,
                status=ShieldCheckStatus.WARNING,
                reason="Proposed action has a CRITICAL customer impact. Escalating for human review.",
                details={"customer_impact": proposal.customer_impact.value}
            )

        # 2. Block/restrict actions check
        # Actions that block customers or permanently restrict transaction recovery must be manually reviewed
        if proposal.action in ("BLOCK_TRANSACTION", "DO_NOT_RETRY"):
            return CheckResultSchema(
                check=self.check_name,
                status=ShieldCheckStatus.WARNING,
                reason=f"Action '{proposal.action}' blocks or permanently restricts customer access. Escalating for manual review.",
                details={"action": proposal.action, "customer_impact": proposal.customer_impact.value}
            )

        return CheckResultSchema(
            check=self.check_name,
            status=ShieldCheckStatus.PASSED,
            reason="Customer impact is within acceptable risk boundaries."
        )
