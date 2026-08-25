from decimal import Decimal
import uuid
from sqlalchemy.orm import Session
from app.agents.base import BaseAgent
from app.agents.recovery.context import gather_recovery_context
from app.llm.provider import LLMProvider
from app.database.models.agent import Agent
from app.database.models.agent_proposal import AgentProposal
from app.database.models.enums import ProposalStatus, TransactionStatus

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

        if tx.status not in (TransactionStatus.FAILED, TransactionStatus.BLOCKED):
            raise ValueError(f"Transaction with ID {event_id} has status '{tx.status.value}' and cannot be processed for recovery.")

        # RAG - retrieve relevant policies for this merchant & transaction failure context
        from app.rag.retrieval import retrieve_relevant_policies_sync
        
        query_text = f"Payment failure: {tx.payment_method} transaction of {tx.amount} {tx.currency} with status {tx.status.value}"
        retrieved_policies = retrieve_relevant_policies_sync(db, tx.merchant_id, query_text, limit=3)
        
        policies_context = ""
        if retrieved_policies:
            policies_context += "\n- Retrieved Merchant Policies (RAG Context):\n"
            for i, p in enumerate(retrieved_policies, 1):
                policies_context += f"  {i}. {p.policy_name} (Key: {p.policy_key}):\n"
                policies_context += f"     Description: {p.description or 'None'}\n"
                policies_context += f"     Similarity Score: {p.similarity_score:.4f}\n"
                policies_context += f"     Rules:\n"
                indented_content = "\n".join(f"       {line}" for line in p.document_content.splitlines())
                policies_context += f"{indented_content}\n"
        else:
            policies_context += "\n- Retrieved Merchant Policies: None configured.\n"

        # Construct context prompt for Gemini
        prompt = f"""
You are the Payment Recovery Agent of AgentShield.
Your task is to analyze the failed transaction details and previous recovery attempts to propose a recovery action.

[CRITICAL INSTRUCTIONS]
1. Use ONLY the provided context. Do NOT assume or invent facts.
2. Propose actions sequentially based on the history of previous proposals (e.g., if there are no prior proposals, propose a WAIT_AND_RETRY; if prior retries exist, escalate to REQUEST_NEW_PAYMENT_METHOD or ESCALATE_TO_SUPPORT).
3. You must output ONLY a valid JSON object matching the schema below. No explanation, markdown formatting, or surrounding text.
4. Allowed actions: WAIT_AND_RETRY, REQUEST_NEW_PAYMENT_METHOD, ESCALATE_TO_SUPPORT, DO_NOT_RETRY.
5. Align your proposal rules (e.g., maximum recovery attempts, wait duration, escalation triggers) with the retrieved merchant policies where applicable.

[REQUIRED JSON SCHEMA]
{{
  "proposed_action": "One of the allowed actions above",
  "action_parameters": {{ "wait_hours": 24 }} or null,  // Wait hours is required ONLY for WAIT_AND_RETRY
  "confidence": 0.82,  // A float value between 0.0 and 1.0
  "evidence": ["CARD_DECLINED_INSUFFICIENT_FUNDS"],  // List of string evidence codes
  "reason_summary": "Short explanation detailing the recovery strategy decision",
  "financial_impact": "LOW",  // One of LOW, MEDIUM, HIGH, CRITICAL
  "customer_impact": "LOW"    // One of LOW, MEDIUM, HIGH, CRITICAL
}}

[CONTEXT]
- Failed Transaction:
  - ID: {tx.id}
  - Amount: {tx.amount} {tx.currency}
  - Payment Method: {tx.payment_method}
  - Current Status: {tx.status.value}
- Customer Profile:
  - Name: {customer.full_name}
- Previous Recovery Proposals for this Transaction (Retry History):
  - Count of previous attempts: {len(previous_proposals)}
  - Details: {[(p.action, p.created_at, p.status.value) for p in previous_proposals]}
{policies_context}
"""

        allowed_actions = ["WAIT_AND_RETRY", "REQUEST_NEW_PAYMENT_METHOD", "ESCALATE_TO_SUPPORT", "DO_NOT_RETRY"]

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
