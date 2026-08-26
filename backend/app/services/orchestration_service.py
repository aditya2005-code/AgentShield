import logging
import uuid
from typing import List, Dict, Any, Optional
from sqlalchemy.orm import Session

from app.database.models.agent import Agent
from app.database.models.agent_proposal import AgentProposal
from app.database.models.shield_decision import ShieldDecision
from app.database.models.audit_log import AuditLog
from app.database.models.transaction import Transaction
from app.database.models.customer import Customer
from app.database.models.merchant import Merchant
from app.database.models.enums import AgentType, ProposalStatus, AuditEventType, TransactionStatus, ShieldDecisionType
from app.agents.router import execute_agent
from app.agentshield.service import evaluate_proposal

logger = logging.getLogger(__name__)

def orchestrate_agent(
    agent_type: AgentType,
    event_type: str,
    event_id: str,
    merchant_id: uuid.UUID,
    db: Session
) -> AgentProposal:
    """
    Executes a single agent, respecting idempotency constraints.
    """
    # 1. Load Agent
    agent = db.query(Agent).filter(Agent.agent_type == agent_type).first()
    if not agent:
        raise ValueError(f"Agent '{agent_type.value}' is not registered.")

    # 2. Check Idempotency (Existing Pending Proposal)
    existing = db.query(AgentProposal).filter(
        AgentProposal.agent_id == agent.id,
        AgentProposal.event_type == event_type,
        AgentProposal.event_id == event_id,
        AgentProposal.status == ProposalStatus.PENDING
    ).first()
    if existing:
        return existing

    # 3. Dynamic execution
    proposal = execute_agent(agent_type, event_type, event_id, str(merchant_id), db)
    db.add(proposal)
    db.flush()

    # 4. Create Proposal Audit Log
    audit_log = AuditLog(
        merchant_id=merchant_id,
        agent_id=agent.id,
        proposal_id=proposal.id,
        event_type=AuditEventType.AGENT_PROPOSAL_CREATED,
        action="AGENT_PROPOSAL_CREATED",
        details={
            "action": proposal.action,
            "confidence": float(proposal.confidence),
            "evidence": proposal.evidence,
            "reason": proposal.reason_summary
        }
    )
    db.add(audit_log)
    db.commit()
    db.refresh(proposal)
    return proposal

def process_event_orchestration(
    db: Session,
    event_type: str,
    event_id: str
) -> Dict[str, Any]:
    """
    Orchestrates multiple agents, gathers proposals, evaluates decisions,
    resolves decision conflicts, and returns the aggregated E2E state.
    """
    event_type_norm = event_type.upper()
    proposals: List[AgentProposal] = []
    executed_agents: List[str] = []
    status = "COMPLETED"
    merchant_id: Optional[uuid.UUID] = None

    # 1. Context Gathering & Applicable Agent Selection
    applicable_agents = []  # List of tuples (AgentType, event_type, event_id)

    if event_type_norm in ("TRANSACTION", "PAYMENT_FAILURE"):
        try:
            tx_uuid = uuid.UUID(event_id)
        except ValueError:
            raise ValueError(f"Invalid transaction UUID format: {event_id}")

        tx = db.query(Transaction).filter(Transaction.id == tx_uuid).first()
        if not tx:
            raise ValueError(f"Transaction with ID {event_id} not found.")

        merchant_id = tx.merchant_id
        
        # Fraud Agent is always applicable to transaction events
        applicable_agents.append((AgentType.FRAUD, "TRANSACTION", event_id))

        # Recovery Agent is applicable to payment failure status
        if tx.status in (TransactionStatus.FAILED, TransactionStatus.BLOCKED) or event_type_norm == "PAYMENT_FAILURE":
            applicable_agents.append((AgentType.RECOVERY, "PAYMENT_FAILURE", event_id))

        # Growth Agent is applicable if transaction succeeds
        if tx.status == TransactionStatus.SUCCESS:
            applicable_agents.append((AgentType.GROWTH, "GROWTH_OPPORTUNITY", str(tx.customer_id)))

    elif event_type_norm == "GROWTH_OPPORTUNITY":
        try:
            cust_uuid = uuid.UUID(event_id)
        except ValueError:
            raise ValueError(f"Invalid customer UUID format: {event_id}")

        customer = db.query(Customer).filter(Customer.id == cust_uuid).first()
        if not customer:
            raise ValueError(f"Customer with ID {event_id} not found.")

        merchant_id = customer.merchant_id
        applicable_agents.append((AgentType.GROWTH, "GROWTH_OPPORTUNITY", event_id))

    else:
        raise ValueError(f"Unsupported event type: {event_type}")

    if not merchant_id:
        raise ValueError("Could not determine merchant context for this event.")

    # 2. Sequential Execution & Resilience Handling
    for agent_type, ev_type, ev_id in applicable_agents:
        try:
            proposal = orchestrate_agent(agent_type, ev_type, ev_id, merchant_id, db)
            proposals.append(proposal)
            executed_agents.append(agent_type.value)
        except Exception as e:
            logger.error(f"Specialized Agent {agent_type.value} execution failed: {e}", exc_info=True)
            status = "DEGRADED"

    # If all agents failed or no agents executed
    if not proposals:
        return {
            "event_id": event_id,
            "status": "FAILED",
            "executed_agents": executed_agents,
            "proposals": [],
            "final_decision": None,
            "decision_id": None,
            "decision_details": []
        }

    # 3. Decision Evaluation & Conflict Resolution
    decisions: List[ShieldDecision] = []
    final_decision_value = "APPROVE"
    final_decision_id: Optional[uuid.UUID] = None

    decision_priority = {
        "REJECT": 4,
        "ESCALATE": 3,
        "MODIFY": 2,
        "APPROVE": 1
    }

    for prop in proposals:
        try:
            decision = evaluate_proposal(db, prop.id)
            decisions.append(decision)
            
            # Select most protective decision based on priority
            cur_priority = decision_priority.get(decision.decision.value, 1)
            resolved_priority = decision_priority.get(final_decision_value, 1)
            if cur_priority >= resolved_priority:
                final_decision_value = decision.decision.value
                final_decision_id = decision.id
        except Exception as e:
            logger.error(f"AgentShield failed to evaluate proposal {prop.id}: {e}", exc_info=True)
            status = "DEGRADED"

    # 4. Formulate structured response
    proposal_summaries = [
        {
            "proposal_id": str(p.id),
            "agent_key": p.agent.agent_key,
            "action": p.action,
            "status": p.status.value
        } for p in proposals
    ]

    decision_summaries = [
        {
            "decision_id": str(d.id),
            "decision": d.decision.value,
            "final_action": d.final_action,
            "reason": d.reason
        } for d in decisions
    ]

    return {
        "event_id": event_id,
        "status": status,
        "executed_agents": executed_agents,
        "proposals": proposal_summaries,
        "final_decision": final_decision_value,
        "decision_id": str(final_decision_id) if final_decision_id else None,
        "decision_details": decision_summaries
    }
