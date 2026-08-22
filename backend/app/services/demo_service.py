import uuid
from typing import Optional, Dict, Any, List
from sqlalchemy.orm import Session
from app.database.models import (
    Agent, AgentProposal, ShieldDecision, MerchantPolicy, AuditLog, Transaction
)

def get_scenarios() -> List[str]:
    return ["fraud", "recovery", "growth"]

def get_scenario_by_type(db: Session, scenario_type: str) -> Optional[Dict[str, Any]]:
    # Map scenario_type to agent_key
    agent_key = f"{scenario_type}_agent"
    
    # 1. Fetch Agent
    agent = db.query(Agent).filter(Agent.agent_key == agent_key).first()
    if not agent:
        return None
        
    # 2. Fetch Proposal for this agent
    proposal = db.query(AgentProposal).filter(AgentProposal.agent_id == agent.id).order_by(AgentProposal.created_at.desc()).first()
    if not proposal:
        return None

    # 3. Fetch Event Context
    event_data = {}
    if scenario_type in ("fraud", "recovery"):
        try:
            tx_id = uuid.UUID(proposal.event_id)
            tx = db.query(Transaction).filter(Transaction.id == tx_id).first()
            if tx:
                event_data = {
                    "transaction_id": str(tx.id),
                    "external_transaction_id": tx.external_transaction_id,
                    "amount": float(tx.amount),
                    "currency": tx.currency,
                    "payment_method": tx.payment_method,
                    "location": tx.location,
                    "status": tx.status.value,
                    "occurred_at": tx.occurred_at.isoformat()
                }
        except ValueError:
            event_data = {"error": f"Invalid event_id UUID: {proposal.event_id}"}
    else:
        # Growth scenario uses growth opportunity custom event
        event_data = {
            "event_type": "GROWTH_OPPORTUNITY",
            "event_id": proposal.event_id,
            "details": {
                "reason": "Cart abandonment of high value item",
                "value": 45000.0,
                "customer_name": "Rohan Das"
            }
        }

    # 4. Fetch Merchant Policies
    policies = db.query(MerchantPolicy).filter(
        MerchantPolicy.merchant_id == proposal.merchant_id,
        MerchantPolicy.is_active == True
    ).all()

    # 5. Fetch Shield Decision
    decision = db.query(ShieldDecision).filter(ShieldDecision.proposal_id == proposal.id).first()

    # 6. Fetch related Audit Logs
    audit_logs = db.query(AuditLog).filter(AuditLog.proposal_id == proposal.id).order_by(AuditLog.created_at.asc()).all()

    return {
        "event": event_data,
        "agent": agent,
        "proposal": proposal,
        "merchant_policies": policies,
        "shield_decision": decision,
        "audit_logs": audit_logs
    }
