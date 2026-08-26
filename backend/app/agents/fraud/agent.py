import logging
from decimal import Decimal
import uuid
from sqlalchemy.orm import Session
from app.agents.base import BaseAgent
from app.agents.fraud.context import gather_fraud_context
from app.llm.provider import LLMProvider
from app.database.models.agent import Agent
from app.database.models.agent_proposal import AgentProposal
from app.database.models.enums import ProposalStatus
from app.ml.inference.service import FraudPredictionService

logger = logging.getLogger(__name__)

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

        # Deterministic extraction of ML features
        ml_signal = None
        feature_extraction_failed = False
        features = {}
        
        try:
            # 1. Amount
            features["Amount"] = float(tx.amount)
            
            # 2. Merchant_Category (mapped from merchant slug)
            merchant_slug = context.merchant.slug
            merchant_category_map = {
                "velocart-electronics": "Electronics",
                "scribeflow-premium": "Online_Services",
                "novapixel-assets": "Online_Services"
            }
            if merchant_slug not in merchant_category_map:
                raise ValueError(f"Unknown merchant category mapping for slug: {merchant_slug}")
            features["Merchant_Category"] = merchant_category_map[merchant_slug]
            
            # 3. Device_Type (mapped from device type string)
            if device is None or not device.device_type:
                raise ValueError("Device information is missing; cannot extract Device_Type.")
            d_type = device.device_type.lower()
            if "android" in d_type:
                features["Device_Type"] = "Android"
            elif "ios" in d_type:
                features["Device_Type"] = "iOS"
            else:
                features["Device_Type"] = "Web_Browser"
                
            # 4. Distance_from_Home (anomalous if location is different from successful history)
            if tx.location in successful_locations:
                features["Distance_from_Home"] = 0.0123
            else:
                features["Distance_from_Home"] = 4.8088
                
            # 5. IP_Risk_Score
            if tx.location in successful_locations and device.is_trusted:
                features["IP_Risk_Score"] = 0.05
            elif tx.location not in successful_locations:
                features["IP_Risk_Score"] = 0.85
            else:
                features["IP_Risk_Score"] = 0.15
                
            # 6. Avg_Spending_Habit (average of historical successful transactions)
            successful_txs = [t for t in history if t.status.value == "SUCCESS"]
            if successful_txs:
                features["Avg_Spending_Habit"] = float(sum(t.amount for t in successful_txs) / len(successful_txs))
            else:
                features["Avg_Spending_Habit"] = float(tx.amount)
                
            # 7. Is_Weekend, Is_Night_Transaction, Transaction_Hour, Day_of_Week
            occurred = tx.occurred_at
            features["Transaction_Hour"] = occurred.hour
            features["Day_of_Week"] = occurred.weekday()
            features["Is_Weekend"] = 1 if features["Day_of_Week"] in (5, 6) else 0
            features["Is_Night_Transaction"] = 1 if features["Transaction_Hour"] in (22, 23, 0, 1, 2, 3, 4, 5) else 0
            
        except Exception as e:
            logger.warning(f"ML feature extraction failed: {e}")
            feature_extraction_failed = True

        # Run model prediction internally using service layer
        if not feature_extraction_failed:
            try:
                fraud_service = FraudPredictionService()
                ml_signal = fraud_service.predict_transaction(features)
                logger.info(
                    f"ML Fraud signal obtained: probability={ml_signal.fraud_probability}, "
                    f"risk_level={ml_signal.risk_level.value}, is_fraud={ml_signal.is_fraud}"
                )
            except Exception as e:
                logger.error(f"ML prediction execution failed: {e}")
                ml_signal = None

        # Construct ML prompt section if available
        ml_prompt_section = ""
        if ml_signal is not None:
            ml_prompt_section = f"""
[FRAUD ML EVIDENCE]
- Fraud probability: {ml_signal.fraud_probability:.4f}
- Fraud risk level: {ml_signal.risk_level.value}
- Classification threshold: {ml_signal.threshold}
- Model version: {ml_signal.model_version}
- Model classification: {"FRAUD" if ml_signal.is_fraud else "CLEAN"}

[LLM INSTRUCTIONS FOR ML EVIDENCE]
- The ML fraud probability is a model-generated signal.
- Do not alter, override, or recalculate the probability. Do not invent another probability.
- Interpret this signal together with the transaction context.
- Explain relevant risk factors in the 'reason_summary'.
- Return only the existing required structured output.
- Do not make the final payment decision. AgentShield makes the final deterministic decision.
"""
        else:
            ml_prompt_section = """
[FRAUD ML EVIDENCE]
- ML fraud prediction signal is currently UNAVAILABLE.
- Rely solely on the transaction context below.
"""

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
{ml_prompt_section}
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

        # Persist ML details in action_parameters for auditing
        if ml_signal is not None:
            proposal_params = {
                "fraud_probability": ml_signal.fraud_probability,
                "fraud_risk_level": ml_signal.risk_level.value,
                "ml_model_version": ml_signal.model_version
            }
        else:
            proposal_params = {
                "ml_signal_available": False
            }

        # Override proposal action parameters with our structured ML context
        if output.get("action_parameters") is not None:
            proposal_params.update(output["action_parameters"])

        return AgentProposal(
            agent_id=agent.id,
            merchant_id=tx.merchant_id,
            event_type=event_type,
            event_id=event_id,
            action=output["proposed_action"],
            action_parameters=proposal_params,
            confidence=Decimal(str(output["confidence"])),
            financial_impact=output["financial_impact"],
            customer_impact=output["customer_impact"],
            evidence=output["evidence"],
            reason_summary=output["reason_summary"],
            status=ProposalStatus.PENDING
        )
