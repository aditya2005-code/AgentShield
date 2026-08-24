from app.agentshield.checks.base import BaseShieldCheck
from app.agentshield.context import EvaluationContext
from app.agentshield.schemas import CheckResultSchema
from app.database.models.enums import ShieldCheckStatus

class PolicyCheck(BaseShieldCheck):
    @property
    def check_name(self) -> str:
        return "merchant_policy"

    def run(self, context: EvaluationContext) -> CheckResultSchema:
        proposal = context.proposal
        policies = context.policies

        # Map active policies by key
        policies_dict = {p.policy_key: p for p in policies if p.is_active}

        # 1. Discount Limit Policy Checks
        if proposal.action == "APPLY_DISCOUNT":
            policy = policies_dict.get("max_discount_percent")
            if policy:
                allowed_percent = policy.policy_value.get("value")
                params = proposal.action_parameters or {}
                proposed_percent = params.get("discount_percent")
                
                if proposed_percent is not None and allowed_percent is not None:
                    if proposed_percent > allowed_percent:
                        return CheckResultSchema(
                            check=self.check_name,
                            status=ShieldCheckStatus.WARNING,
                            policy_key="max_discount_percent",
                            original_value=proposed_percent,
                            allowed_value=allowed_percent,
                            modification_required=True,
                            reason=f"Proposed discount percent ({proposed_percent}%) exceeds merchant maximum limit of {allowed_percent}%."
                        )

        # 2. Retry Attempt Limit Policy Checks
        if proposal.action == "WAIT_AND_RETRY":
            policy = policies_dict.get("max_recovery_retries")
            if policy:
                allowed_retries = policy.policy_value.get("value")
                if allowed_retries is not None:
                    # If prior attempts met or exceeded limit
                    if context.retry_count >= allowed_retries:
                        return CheckResultSchema(
                            check=self.check_name,
                            status=ShieldCheckStatus.WARNING,
                            policy_key="max_recovery_retries",
                            original_value=context.retry_count,
                            allowed_value=allowed_retries,
                            modification_required=False,
                            reason=f"Recovery attempt count ({context.retry_count}) has met or exceeded merchant maximum recovery retries limit of {allowed_retries}."
                        )

        return CheckResultSchema(
            check=self.check_name,
            status=ShieldCheckStatus.PASSED,
            reason="Proposal conforms to all active merchant policies."
        )
