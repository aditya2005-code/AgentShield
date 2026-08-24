from app.agentshield.checks.base import BaseShieldCheck
from app.agentshield.context import EvaluationContext
from app.agentshield.schemas import CheckResultSchema
from app.database.models.enums import ShieldCheckStatus, ImpactLevel

class RiskCheck(BaseShieldCheck):
    @property
    def check_name(self) -> str:
        return "risk_safety"

    def run(self, context: EvaluationContext) -> CheckResultSchema:
        proposal = context.proposal

        # 1. Low absolute confidence check
        if proposal.confidence < 0.50:
            return CheckResultSchema(
                check=self.check_name,
                status=ShieldCheckStatus.WARNING,
                reason=f"Proposal confidence ({proposal.confidence}) is below safe auto-approve threshold of 0.50. Escalating.",
                details={"confidence": float(proposal.confidence)}
            )

        # 2. Low confidence + high/critical impact check
        high_impacts = (ImpactLevel.HIGH, ImpactLevel.CRITICAL)
        if proposal.confidence < 0.70:
            if proposal.financial_impact in high_impacts or proposal.customer_impact in high_impacts:
                return CheckResultSchema(
                    check=self.check_name,
                    status=ShieldCheckStatus.WARNING,
                    reason=f"Low proposal confidence ({proposal.confidence}) for high-impact action. Escalating.",
                    details={
                        "confidence": float(proposal.confidence),
                        "financial_impact": proposal.financial_impact.value,
                        "customer_impact": proposal.customer_impact.value
                    }
                )

        # 3. Missing evidence check for critical security actions
        if proposal.action in ("BLOCK_TRANSACTION", "STEP_UP_VERIFICATION"):
            if not proposal.evidence:
                return CheckResultSchema(
                    check=self.check_name,
                    status=ShieldCheckStatus.FAILED,
                    reason=f"Critical safety violation: action '{proposal.action}' proposed without supporting evidence.",
                    details={"action": proposal.action, "evidence": proposal.evidence}
                )

        return CheckResultSchema(
            check=self.check_name,
            status=ShieldCheckStatus.PASSED,
            reason="Proposal confidence and safety evidence meet auto-approve requirements."
        )
