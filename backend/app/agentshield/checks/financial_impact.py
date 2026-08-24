from app.agentshield.checks.base import BaseShieldCheck
from app.agentshield.context import EvaluationContext
from app.agentshield.schemas import CheckResultSchema
from app.database.models.enums import ShieldCheckStatus, ImpactLevel

class FinancialImpactCheck(BaseShieldCheck):
    @property
    def check_name(self) -> str:
        return "financial_impact"

    def run(self, context: EvaluationContext) -> CheckResultSchema:
        proposal = context.proposal
        transaction = context.transaction
        policies = context.policies

        # Map active policies by key
        policies_dict = {p.policy_key: p for p in policies if p.is_active}

        # 1. Proposal financial impact level check
        if proposal.financial_impact == ImpactLevel.CRITICAL:
            return CheckResultSchema(
                check=self.check_name,
                status=ShieldCheckStatus.WARNING,
                reason="Proposed action has a CRITICAL financial impact. Escalating for manual review.",
                details={"financial_impact": proposal.financial_impact.value}
            )

        # 2. High value transaction discount threshold check
        high_value_threshold = 50000  # Default safe threshold
        policy = policies_dict.get("high_value_threshold")
        if policy:
            high_value_threshold = policy.policy_value.get("value", high_value_threshold)

        if transaction and transaction.amount >= high_value_threshold:
            # Discounts or promotions on high-value items must be reviewed manually
            if proposal.action in ("APPLY_DISCOUNT", "SEND_PROMOTION"):
                return CheckResultSchema(
                    check=self.check_name,
                    status=ShieldCheckStatus.WARNING,
                    reason=f"Transaction value ({transaction.amount}) is above the high value threshold of {high_value_threshold}. Action '{proposal.action}' requires escalation.",
                    details={
                        "transaction_amount": float(transaction.amount),
                        "high_value_threshold": high_value_threshold,
                        "action": proposal.action
                    }
                )

        return CheckResultSchema(
            check=self.check_name,
            status=ShieldCheckStatus.PASSED,
            reason="Financial impact is within acceptable risk parameters."
        )
