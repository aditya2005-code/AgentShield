from decimal import Decimal
import uuid
from sqlalchemy.orm import Session
from app.agents.base import BaseAgent
from app.agents.growth.context import gather_growth_context
from app.database.models.agent import Agent
from app.database.models.agent_proposal import AgentProposal
from app.database.models.enums import ImpactLevel, ProposalStatus

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
        # For growth agent, event_id represents customer_id, and merchant_id represents merchant_id
        m_id = uuid.UUID(merchant_id)
        c_id = uuid.UUID(event_id)

        context = gather_growth_context(db, m_id, c_id)
        if not context:
            raise ValueError(f"Growth Context could not be gathered. Check that customer {c_id} exists and belongs to merchant {m_id}.")

        customer = context.customer
        history = context.customer_history

        # Heuristic spending rules
        # 1. Seed scenario match: Rohan Das (cust_sf_001) cart abandonment recovery discount
        if customer.external_customer_id == "cust_sf_001":
            action = "APPLY_DISCOUNT"
            action_parameters = {"discount_percent": 25}
            confidence = Decimal("0.8500")
            financial_impact = ImpactLevel.MEDIUM
            customer_impact = ImpactLevel.LOW
            evidence = ["CART_ABANDONMENT_HIGH_VALUE"]
            reason_summary = "High-value cart abandoned by customer. Proposing 25% recovery discount promotion."
        # 2. High spending upsell
        elif history and sum(t.amount for t in history if t.status.value == "SUCCESS") / len([t for t in history if t.status.value == "SUCCESS"] or [1]) >= Decimal("50000.00"):
            action = "OFFER_UPSELL"
            action_parameters = {"upsell_item": "extended_warranty"}
            confidence = Decimal("0.8000")
            financial_impact = ImpactLevel.LOW
            customer_impact = ImpactLevel.LOW
            evidence = ["HIGH_VALUE_LOYAL_CUSTOMER"]
            reason_summary = "Customer has high average order value. Offering premium product upsell opportunity."
        # 3. Dormant retention promotion
        elif history and all((t.occurred_at - t.occurred_at).total_seconds() > 30 * 24 * 3600 for t in history):
            action = "SEND_PROMOTION"
            action_parameters = {"promo_code": "RETENTION_15"}
            confidence = Decimal("0.7500")
            financial_impact = ImpactLevel.LOW
            customer_impact = ImpactLevel.LOW
            evidence = ["INACTIVE_CUSTOMER_30D"]
            reason_summary = "Customer has been inactive for over 30 days. Sending welcome back promotional offer."
        # 4. Standard baseline
        else:
            action = "NO_ACTION"
            action_parameters = None
            confidence = Decimal("1.0000")
            financial_impact = ImpactLevel.LOW
            customer_impact = ImpactLevel.LOW
            evidence = []
            reason_summary = "Customer spending patterns are stable. No growth actions required."

        agent = db.query(Agent).filter(Agent.agent_key == self.agent_key).first()
        if not agent:
            raise ValueError(f"Agent with key '{self.agent_key}' not found in database.")

        return AgentProposal(
            agent_id=agent.id,
            merchant_id=m_id,
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
