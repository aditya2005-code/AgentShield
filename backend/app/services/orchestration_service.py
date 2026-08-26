import logging
import uuid
from typing import List, Dict, Any, Optional
from sqlalchemy.orm import Session
from sqlalchemy.exc import IntegrityError

from app.database.models.agent import Agent
from app.database.models.agent_proposal import AgentProposal
from app.database.models.shield_decision import ShieldDecision
from app.database.models.audit_log import AuditLog
from app.database.models.transaction import Transaction
from app.database.models.customer import Customer
from app.database.models.merchant import Merchant
from app.database.models.event_workflow import EventWorkflow
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
    Reuses existing proposals (regardless of status) under retry/resume scenarios.
    """
    # 1. Load Agent
    agent = db.query(Agent).filter(Agent.agent_type == agent_type).first()
    if not agent:
        raise ValueError(f"Agent '{agent_type.value}' is not registered.")

    # 2. Check Idempotency (Existing Proposal for event_id and agent_id)
    existing = db.query(AgentProposal).filter(
        AgentProposal.agent_id == agent.id,
        AgentProposal.event_type == event_type,
        AgentProposal.event_id == event_id
    ).first()
    if existing:
        logger.info(f"Reusing existing proposal '{existing.id}' for agent '{agent_type.value}' and event '{event_id}'.")
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

    # 1. Context Gathering & Applicable Agent Selection (Objective 1 Routing Validation)
    applicable_agents = []  # List of tuples (AgentType, event_type, event_id)

    if event_type_norm == "TRANSACTION":
        try:
            tx_uuid = uuid.UUID(event_id)
        except ValueError:
            raise ValueError(f"Invalid transaction UUID format: {event_id}")

        tx = db.query(Transaction).filter(Transaction.id == tx_uuid).first()
        if not tx:
            raise ValueError(f"Transaction with ID {event_id} not found.")

        merchant_id = tx.merchant_id
        
        # TRANSACTION: Always execute FraudAgent
        applicable_agents.append((AgentType.FRAUD, "TRANSACTION", event_id))

        # TRANSACTION: If transaction status is FAILED or BLOCKED, execute RecoveryAgent
        if tx.status in (TransactionStatus.FAILED, TransactionStatus.BLOCKED):
            applicable_agents.append((AgentType.RECOVERY, "PAYMENT_FAILURE", event_id))

        # TRANSACTION: If transaction status is SUCCESS, execute GrowthAgent
        if tx.status == TransactionStatus.SUCCESS:
            applicable_agents.append((AgentType.GROWTH, "GROWTH_OPPORTUNITY", str(tx.customer_id)))

    elif event_type_norm == "PAYMENT_FAILURE":
        try:
            tx_uuid = uuid.UUID(event_id)
        except ValueError:
            raise ValueError(f"Invalid transaction UUID format: {event_id}")

        tx = db.query(Transaction).filter(Transaction.id == tx_uuid).first()
        if not tx:
            raise ValueError(f"Transaction with ID {event_id} not found.")

        merchant_id = tx.merchant_id
        
        # PAYMENT_FAILURE: execute RecoveryAgent
        applicable_agents.append((AgentType.RECOVERY, "PAYMENT_FAILURE", event_id))
        
        # PAYMENT_FAILURE: execute FraudAgent only when sufficient transaction context exists
        applicable_agents.append((AgentType.FRAUD, "TRANSACTION", event_id))

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

    # Helper response for processing status
    in_progress_response = {
        "event_id": event_id,
        "status": "PROCESSING",
        "executed_agents": [],
        "proposals": [],
        "final_decision": None,
        "decision_id": None,
        "decision_details": []
    }

    # 2. Database-Backed Idempotency & Lifecycle Check (Objectives 2, 3, 4)
    workflow = db.query(EventWorkflow).filter_by(event_type=event_type_norm, event_id=event_id).first()
    
    if workflow:
        if workflow.status == "COMPLETED":
            logger.info(f"Event '{event_id}' already completed. Returning cached result.")
            return workflow.result
        elif workflow.status == "PROCESSING":
            logger.info(f"Event '{event_id}' is currently processing. Returning in-progress response.")
            return in_progress_response
        elif workflow.status == "FAILED":
            logger.info(f"Event '{event_id}' previously failed. Transitioning to PROCESSING for retry.")
            workflow.status = "PROCESSING"
            workflow.result = None
            db.commit()
    else:
        # Insert a new EventWorkflow record with status 'PROCESSING' to act as a lock
        workflow = EventWorkflow(
            event_type=event_type_norm,
            event_id=event_id,
            merchant_id=merchant_id,
            status="PROCESSING"
        )
        db.add(workflow)
        try:
            db.commit()
        except IntegrityError:
            # unique constraint violation from concurrent request
            db.rollback()
            workflow = db.query(EventWorkflow).filter_by(event_type=event_type_norm, event_id=event_id).first()
            if workflow:
                if workflow.status == "COMPLETED":
                    return workflow.result
                elif workflow.status == "PROCESSING":
                    return in_progress_response
            # Fallback failed
            return in_progress_response

    # 3. Sequential Execution & Resilience Handling
    execution_failed = False
    for agent_type, ev_type, ev_id in applicable_agents:
        try:
            proposal = orchestrate_agent(agent_type, ev_type, ev_id, merchant_id, db)
            proposals.append(proposal)
            executed_agents.append(agent_type.value)
        except Exception as e:
            logger.error(f"Specialized Agent {agent_type.value} execution failed: {e}", exc_info=True)
            status = "DEGRADED"
            execution_failed = True

    # If all agents failed or no agents executed
    if not proposals:
        workflow.status = "FAILED"
        workflow.result = None
        db.commit()
        return {
            "event_id": event_id,
            "status": "FAILED",
            "executed_agents": executed_agents,
            "proposals": [],
            "final_decision": None,
            "decision_id": None,
            "decision_details": []
        }

    # 4. Decision Evaluation & Conflict Resolution
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

    # 5. Formulate structured response and update database state
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

    result_payload = {
        "event_id": event_id,
        "status": status,
        "executed_agents": executed_agents,
        "proposals": proposal_summaries,
        "final_decision": final_decision_value,
        "decision_id": str(final_decision_id) if final_decision_id else None,
        "decision_details": decision_summaries
    }

    workflow.status = "COMPLETED"
    workflow.result = result_payload
    db.commit()

    return result_payload
