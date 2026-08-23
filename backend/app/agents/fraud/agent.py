from decimal import Decimal
import uuid
from sqlalchemy.orm import Session
from app.agents.base import BaseAgent
from app.agents.fraud.context import gather_fraud_context
from app.database.models.agent import Agent
from app.database.models.agent_proposal import AgentProposal
from app.database.models.enums import ImpactLevel, ProposalStatus

class FraudAgent(BaseAgent):
    @property
    def agent_key(self) -> str:
        return "fraud_agent"

    def execute(
        self,
        event_type: str,
        event_id: str,
        merchant_id: str,
        db: Session
    ) -> AgentProposal:
        if event_type.upper() != "TRANSACTION":
            raise ValueError(f"Fraud Agent only supports event_type 'TRANSACTION', got '{event_type}'")

        tx_id = uuid.UUID(event_id)
        context = gather_fraud_context(db, tx_id)
        if not context:
            raise ValueError(f"Transaction with ID {event_id} not found in database.")

        tx = context.transaction
        customer = context.customer
        device = context.device
        history = context.customer_history

        evidence = []
        
        # 1. New or untrusted device check
        if device is None or not device.is_trusted:
            evidence.append("NEW_DEVICE")

        # 2. Unusual location check
        # Compare with the location of the customer's previous successful transactions
        successful_locations = {t.location for t in history if t.status.value == "SUCCESS"}
        if successful_locations and tx.location not in successful_locations:
            evidence.append("UNUSUAL_LOCATION")
        elif not successful_locations and history:
            # If they have transaction history but no successful ones, location is unconfirmed
            evidence.append("UNUSUAL_LOCATION")

        # 3. High transaction velocity check
        # Check for another transaction by the same customer within 48 hours
        if history:
            time_diffs = [abs((tx.occurred_at - t.occurred_at).total_seconds()) for t in history]
            min_diff = min(time_diffs) if time_diffs else None
            if min_diff is not None and min_diff < 48 * 3600:
                evidence.append("HIGH_TRANSACTION_VELOCITY")

        # 4. High transaction amount check
        if tx.amount >= Decimal("50000.00"):
            evidence.append("HIGH_TRANSACTION_AMOUNT")

        # Propose Action based on heuristic rules
        if "NEW_DEVICE" in evidence and "UNUSUAL_LOCATION" in evidence:
            action = "STEP_UP_VERIFICATION"
            confidence = Decimal("0.8800")
            financial_impact = ImpactLevel.MEDIUM
            customer_impact = ImpactLevel.MEDIUM
            reason_summary = f"Kabir Singh transaction occurred at anomalous location ({tx.location}) using untrusted device."
        elif "NEW_DEVICE" in evidence and "HIGH_TRANSACTION_AMOUNT" in evidence:
            action = "BLOCK_TRANSACTION"
            confidence = Decimal("0.9200")
            financial_impact = ImpactLevel.HIGH
            customer_impact = ImpactLevel.HIGH
            reason_summary = f"High risk transaction of {tx.amount} {tx.currency} proposed from untrusted device."
        elif len(evidence) > 0:
            action = "ESCALATE_TO_REVIEW"
            confidence = Decimal("0.7500")
            financial_impact = ImpactLevel.MEDIUM
            customer_impact = ImpactLevel.LOW
            reason_summary = f"Transaction flagged with risk signals: {', '.join(evidence)}. Escalated to manual review."
        else:
            action = "ALLOW_TRANSACTION"
            confidence = Decimal("0.9500")
            financial_impact = ImpactLevel.LOW
            customer_impact = ImpactLevel.LOW
            reason_summary = "No anomalous risk signals detected. Allowing transaction."

        agent = db.query(Agent).filter(Agent.agent_key == self.agent_key).first()
        if not agent:
            raise ValueError(f"Agent with key '{self.agent_key}' not found in database.")

        return AgentProposal(
            agent_id=agent.id,
            merchant_id=tx.merchant_id,
            event_type=event_type,
            event_id=event_id,
            action=action,
            action_parameters=None,
            confidence=confidence,
            financial_impact=financial_impact,
            customer_impact=customer_impact,
            evidence=evidence,
            reason_summary=reason_summary,
            status=ProposalStatus.PENDING
        )
