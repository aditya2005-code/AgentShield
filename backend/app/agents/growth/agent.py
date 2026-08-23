from decimal import Decimal
import uuid
from sqlalchemy.orm import Session
from app.agents.base import BaseAgent
from app.agents.growth.context import gather_growth_context
from app.llm.provider import LLMProvider
from app.database.models.agent import Agent
from app.database.models.agent_proposal import AgentProposal
from app.database.models.enums import ProposalStatus

class GrowthAgent(BaseAgent):
    @property
    def agent_key(self) -> str:
        return "growth_agent"

    def execute(
        self,
        event_type: str,
        event_id: str,
        merchant_id: str,
        db: Session
    ) -> AgentProposal:
        m_id = uuid.UUID(merchant_id)
        c_id = uuid.UUID(event_id)

        context = gather_growth_context(db, m_id, c_id)
        if not context:
            raise ValueError(f"Growth Context could not be gathered. Check that customer {c_id} exists and belongs to merchant {m_id}.")

        customer = context.customer
        merchant = context.merchant
        history = context.customer_history

        # Construct context prompt for Gemini
        prompt = f"""
You are the Growth Incentives Agent of AgentShield.
Your task is to analyze the customer shopping history and behavior at this merchant to propose growth incentives or retention activities.

[CRITICAL INSTRUCTIONS]
1. Use ONLY the provided context. Do NOT assume, extrapolate, or invent facts.
2. Formulate promotions or discounts based on behavior (e.g., offer VIP upsell for high average spend, discount code for abandoned carts or dormancy).
3. You must output ONLY a valid JSON object matching the schema below. No explanation, markdown formatting, or surrounding text.
4. Allowed actions: SEND_PROMOTION, APPLY_DISCOUNT, OFFER_UPSELL, NO_ACTION.

[REQUIRED JSON SCHEMA]
{{
  "proposed_action": "One of the allowed actions above",
  "action_parameters": {{ "discount_percent": 25 }} or {{ "promo_code": "RETENTION_15" }} or null,
  "confidence": 0.85,  // A float value between 0.0 and 1.0
  "evidence": ["CART_ABANDONMENT_HIGH_VALUE"],  // List of string evidence codes
  "reason_summary": "Short explanation detailing the customer growth strategy decision",
  "financial_impact": "LOW",  // One of LOW, MEDIUM, HIGH, CRITICAL
  "customer_impact": "LOW"    // One of LOW, MEDIUM, HIGH, CRITICAL
}}

[CONTEXT]
- Customer Profile:
  - ID: {customer.id}
  - External ID: {customer.external_customer_id}
  - Name: {customer.full_name}
  - Risk Category: {customer.risk_profile.value}
- Merchant:
  - ID: {merchant.id}
  - Name: {merchant.name}
- Customer Transaction History at this Merchant:
  - Total transactions count: {len(history)}
  - Details of transactions: {[(t.occurred_at, t.amount, t.status.value) for t in history]}
"""

        allowed_actions = ["SEND_PROMOTION", "APPLY_DISCOUNT", "OFFER_UPSELL", "NO_ACTION"]

        # Call Gemini Reasoning Layer
        provider = LLMProvider()
        output = provider.generate_structured_output(prompt, allowed_actions)

        # Get DB Agent record
        agent = db.query(Agent).filter(Agent.agent_key == self.agent_key).first()
        if not agent:
            raise ValueError(f"Agent with key '{self.agent_key}' not found in database.")

        return AgentProposal(
            agent_id=agent.id,
            merchant_id=m_id,
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
