from typing import List, Tuple, Optional, Any
from app.database.models.enums import ShieldDecisionType, ShieldCheckStatus
from app.agentshield.context import EvaluationContext
from app.agentshield.schemas import CheckResultSchema
from app.agentshield.checks.authorization import AuthorizationCheck
from app.agentshield.checks.policy import PolicyCheck
from app.agentshield.checks.financial_impact import FinancialImpactCheck
from app.agentshield.checks.customer_impact import CustomerImpactCheck
from app.agentshield.checks.risk import RiskCheck

class AgentShieldEngine:
    def __init__(self):
        # Ordered list of guardrail check modules to execute
        self.checks = [
            AuthorizationCheck(),
            PolicyCheck(),
            FinancialImpactCheck(),
            CustomerImpactCheck(),
            RiskCheck()
        ]

    def evaluate(
        self, 
        context: EvaluationContext
    ) -> Tuple[ShieldDecisionType, str, Optional[dict[str, Any]], Optional[dict[str, Any]], List[CheckResultSchema], bool, str]:
        """
        Run all checks and aggregate findings.
        Returns:
            (final_decision, final_action, final_parameters, modified_from, checks_list, requires_human_review, reason_summary)
        """
        check_results: List[CheckResultSchema] = []
        for check in self.checks:
            res = check.run(context)
            check_results.append(res)

        final_decision = ShieldDecisionType.APPROVE
        requires_human_review = False
        reason_parts: List[str] = []

        # Start with the original proposal values
        final_action = context.proposal.action
        final_parameters = dict(context.proposal.action_parameters) if context.proposal.action_parameters else {}
        modified_from = None

        has_reject = False
        has_escalate = False
        has_modify = False

        for res in check_results:
            if res.status == ShieldCheckStatus.FAILED:
                has_reject = True
                reason_parts.append(f"[{res.check.upper()} REJECT] {res.reason}")
            elif res.status == ShieldCheckStatus.WARNING:
                if res.modification_required:
                    has_modify = True
                    reason_parts.append(f"[{res.check.upper()} MODIFY] {res.reason}")
                    
                    # Apply specific modifications
                    if res.policy_key == "max_discount_percent":
                        # Record what we modified from
                        modified_from = {"discount_percent": final_parameters.get("discount_percent")}
                        # Override parameters value with the allowed policy value
                        final_parameters["discount_percent"] = res.allowed_value
                else:
                    has_escalate = True
                    reason_parts.append(f"[{res.check.upper()} ESCALATE] {res.reason}")

        # Resolve priority rules centrally
        if has_reject:
            final_decision = ShieldDecisionType.REJECT
            requires_human_review = True
        elif has_escalate:
            final_decision = ShieldDecisionType.ESCALATE
            requires_human_review = True
        elif has_modify:
            final_decision = ShieldDecisionType.MODIFY
            requires_human_review = False
        else:
            final_decision = ShieldDecisionType.APPROVE
            requires_human_review = False

        # Format reason summary
        if not reason_parts:
            reason_summary = "Proposal successfully approved by all AgentShield guardrails."
        else:
            reason_summary = " | ".join(reason_parts)

        # Clean parameter objects
        final_params_out = final_parameters if final_parameters else None

        return (
            final_decision,
            final_action,
            final_params_out,
            modified_from,
            check_results,
            requires_human_review,
            reason_summary
        )
