from decimal import Decimal
import uuid
from sqlalchemy.orm import Session
from app.agents.base import BaseAgent
from app.agents.fraud.context import gather_fraud_context
from app.llm.provider import LLMProvider
from app.database.models.agent import Agent
from app.database.models.agent_proposal import AgentProposal
from app.database.models.enums import ProposalStatus

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

        # Extract locations of previous successful transactions
        successful_locations = {t.location for t in history if t.status.value == "SUCCESS"}

        # Construct context prompt for Gemini
        prompt = f"""
You are the Fraud Detection Agent of AgentShield, a real-time risk assessment engine.
Your task is to analyze the transaction context below and propose a fraud-related action.

[CRITICAL INSTRUCTIONS]
1. Use ONLY the provided context. Do NOT assume, extrapolate, or invent facts.
2. Provide specific evidence codes based on anomalous signals in the context (e.g., NEW_DEVICE, UNUSUAL_LOCATION, HIGH_TRANSACTION_VELOCITY, HIGH_TRANSACTION_AMOUNT).
3. You must output ONLY a valid JSON object matching the schema below. No explanation, markdown formatting, or surrounding text.
4. Allowed actions: ALLOW_TRANSACTION, STEP_UP_VERIFICATION, BLOCK_TRANSACTION, ESCALATE_TO_REVIEW.

[REQUIRED JSON SCHEMA]
{{
  "proposed_action": "One of the allowed actions above",
  "action_parameters": null,
  "confidence": 0.88,  // A float value between 0.0 and 1.0
  "evidence": ["NEW_DEVICE", "UNUSUAL_LOCATION"],  // List of string evidence codes
  "reason_summary": "Short explanation detailing the anomalous indicators",
  "financial_impact": "LOW",  // One of LOW, MEDIUM, HIGH, CRITICAL
  "customer_impact": "LOW"    // One of LOW, MEDIUM, HIGH, CRITICAL
}}

[CONTEXT]
- Transaction details:
  - ID: {tx.id}
  - Amount: {tx.amount} {tx.currency}
  - Payment Method: {tx.payment_method}
  - Location: {tx.location}
  - Time: {tx.occurred_at}
- Customer Profile:
  - Name: {customer.full_name}
  - Risk Category: {customer.risk_profile.value}
- Device Profile:
  - Trust level: {"Trusted" if (device and device.is_trusted) else "Untrusted/New Device"}
- Customer Location History:
  - Successful locations in history: {list(successful_locations)}
- Transaction Velocity:
  - Recent transactions by customer: {[(t.occurred_at, t.amount, t.location) for t in history]}
"""

        allowed_actions = ["ALLOW_TRANSACTION", "STEP_UP_VERIFICATION", "BLOCK_TRANSACTION", "ESCALATE_TO_REVIEW"]

        # Call Gemini Reasoning Layer
        provider = LLMProvider()
        output = provider.generate_structured_output(prompt, allowed_actions)

        # Get DB Agent record
        agent = db.query(Agent).filter(Agent.agent_key == self.agent_key).first()
        if not agent:
            raise ValueError(f"Agent with key '{self.agent_key}' not found in database.")

        return AgentProposal(
            agent_id=agent.id,
            merchant_id=tx.merchant_id,
            event_type=event_type,
            event_id=event_id,
            action=output["proposed_action"],
            action_parameters=output["action_parameters"],
            confidence=Decimal(str(output["confidence"])),
            financial_impact=output["financial_impact"],
            customer_impact=output["customer_impact"],
            evidence=output["evidence"],
            reason_summary=output["reason_summary"],
            status=ProposalStatus.PENDING
        )
