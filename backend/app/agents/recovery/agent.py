from decimal import Decimal
import uuid
from sqlalchemy.orm import Session
from app.agents.base import BaseAgent
from app.agents.recovery.context import gather_recovery_context
from app.database.models.agent import Agent
from app.database.models.agent_proposal import AgentProposal
from app.database.models.enums import ImpactLevel, ProposalStatus, TransactionStatus

class RecoveryAgent(BaseAgent):
    @property
    def agent_key(self) -> str:
        return "recovery_agent"

    def execute(
        self,
        event_type: str,
        event_id: str,
        merchant_id: str,
        db: Session
    ) -> AgentProposal:
        if event_type.upper() not in ("PAYMENT_FAILURE", "TRANSACTION"):
            raise ValueError(f"Recovery Agent only supports event_type 'PAYMENT_FAILURE' or 'TRANSACTION', got '{event_type}'")

        tx_id = uuid.UUID(event_id)
        context = gather_recovery_context(db, tx_id)
        if not context:
            raise ValueError(f"Transaction with ID {event_id} not found in database.")

        tx = context.transaction
        customer = context.customer
        previous_proposals = context.previous_proposals

        # Validation: ensure transaction is actually in an unsuccessful status
        if tx.status not in (TransactionStatus.FAILED, TransactionStatus.BLOCKED):
            raise ValueError(f"Transaction with ID {event_id} has status '{tx.status.value}' and cannot be processed for recovery.")

        retry_count = len(previous_proposals)

        # Heuristic rules for recovery actions
        if tx.status == TransactionStatus.BLOCKED:
            action = "DO_NOT_RETRY"
            action_parameters = None
            confidence = Decimal("0.9500")
            financial_impact = ImpactLevel.LOW
            customer_impact = ImpactLevel.LOW
            evidence = ["TRANSACTION_BLOCKED_BY_POLICY"]
            reason_summary = "Transaction was blocked due to active security risk policy. Auto recovery bypassed."
        elif retry_count == 0:
            action = "WAIT_AND_RETRY"
            action_parameters = {"wait_hours": 24}
            confidence = Decimal("0.8200")
            financial_impact = ImpactLevel.LOW
            customer_impact = ImpactLevel.LOW
            evidence = ["CARD_DECLINED_INSUFFICIENT_FUNDS"]
            reason_summary = "Credit Card declined for insufficient funds. Proposing temporary wait and retry sequence."
        elif retry_count == 1:
            action = "REQUEST_NEW_PAYMENT_METHOD"
            action_parameters = None
            confidence = Decimal("0.8500")
            financial_impact = ImpactLevel.LOW
            customer_impact = ImpactLevel.LOW
            evidence = ["PREVIOUS_RETRY_FAILED"]
            reason_summary = "Initial wait-and-retry sequence failed. Proposing new payment method request from customer."
        else:
            action = "ESCALATE_TO_SUPPORT"
            action_parameters = None
            confidence = Decimal("0.9000")
            financial_impact = ImpactLevel.LOW
            customer_impact = ImpactLevel.LOW
            evidence = ["MAX_RETRIES_EXCEEDED"]
            reason_summary = "Multiple recovery attempts failed. Escalating transaction to billing support desk."

        agent = db.query(Agent).filter(Agent.agent_key == self.agent_key).first()
        if not agent:
            raise ValueError(f"Agent with key '{self.agent_key}' not found in database.")

        return AgentProposal(
            agent_id=agent.id,
            merchant_id=tx.merchant_id,
            event_type=event_type,
            event_id=event_id,
            action=action,
            action_parameters=action_parameters,
            confidence=confidence,
            financial_impact=financial_impact,
            customer_impact=customer_impact,
            evidence=evidence,
            reason_summary=reason_summary,
            status=ProposalStatus.PENDING
        )
