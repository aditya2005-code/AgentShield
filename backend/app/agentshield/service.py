import uuid
from sqlalchemy.orm import Session
from app.database.models.agent_proposal import AgentProposal
from app.database.models.agent import Agent
from app.database.models.merchant import Merchant
from app.database.models.merchant_policy import MerchantPolicy
from app.database.models.agent_permission import AgentPermission
from app.database.models.customer import Customer
from app.database.models.transaction import Transaction
from app.database.models.shield_decision import ShieldDecision
from app.database.models.audit_log import AuditLog
from app.database.models.enums import ProposalStatus, AuditEventType, ShieldDecisionType
from app.agentshield.context import EvaluationContext
from app.agentshield.engine import AgentShieldEngine

def load_evaluation_context(db: Session, proposal_id: uuid.UUID) -> EvaluationContext:
    proposal = db.query(AgentProposal).filter(AgentProposal.id == proposal_id).first()
    if not proposal:
        raise ValueError(f"Proposal with ID {proposal_id} not found.")

    agent = db.query(Agent).filter(Agent.id == proposal.agent_id).first()
    if not agent:
        raise ValueError("Agent associated with proposal not found.")

    merchant = db.query(Merchant).filter(Merchant.id == proposal.merchant_id).first()
    if not merchant:
        raise ValueError("Merchant associated with proposal not found.")

    policies = (
        db.query(MerchantPolicy)
        .filter(MerchantPolicy.merchant_id == proposal.merchant_id, MerchantPolicy.is_active == True)
        .all()
    )

    permission = (
        db.query(AgentPermission)
        .filter(AgentPermission.agent_id == proposal.agent_id, AgentPermission.action == proposal.action)
        .first()
    )

    customer = None
    transaction = None

    if proposal.event_type.upper() in ("TRANSACTION", "PAYMENT_FAILURE"):
        tx_id = uuid.UUID(proposal.event_id)
        transaction = db.query(Transaction).filter(Transaction.id == tx_id).first()
        if transaction:
            customer = db.query(Customer).filter(Customer.id == transaction.customer_id).first()
    elif proposal.event_type.upper() == "GROWTH_OPPORTUNITY":
        c_id = uuid.UUID(proposal.event_id)
        customer = db.query(Customer).filter(Customer.id == c_id).first()

    # Calculate retry count (how many previous recovery proposals for the same event exist)
    retry_count = 0
    if proposal.action == "WAIT_AND_RETRY":
        retry_count = (
            db.query(AgentProposal)
            .filter(
                AgentProposal.event_id == proposal.event_id,
                AgentProposal.agent_id == proposal.agent_id,
                AgentProposal.id != proposal.id
            )
            .count()
        )

    return EvaluationContext(
        proposal=proposal,
        agent=agent,
        merchant=merchant,
        policies=policies,
        permission=permission,
        customer=customer,
        transaction=transaction,
        retry_count=retry_count,
        db=db
    )

def evaluate_proposal(db: Session, proposal_id: uuid.UUID) -> ShieldDecision:
    # 1. Idempotency Check
    existing = db.query(ShieldDecision).filter(ShieldDecision.proposal_id == proposal_id).first()
    if existing:
        return existing

    # 2. Context Loading
    context = load_evaluation_context(db, proposal_id)
    proposal = context.proposal

    # 3. Decision Evaluation
    engine = AgentShieldEngine()
    decision, final_action, final_params, modified_from, checks, requires_human_review, reason = engine.evaluate(context)

    # 4. Save ShieldDecision
    shield_decision = ShieldDecision(
        proposal_id=proposal_id,
        decision=decision,
        final_action=final_action,
        final_action_parameters=final_params,
        modified_from=modified_from,
        checks=[c.model_dump() for c in checks],
        reason=reason,
        requires_human_review=requires_human_review
    )
    db.add(shield_decision)
    db.flush()

    # 5. Update Proposal lifecycle status (original proposed properties are preserved unchanged)
    if decision == ShieldDecisionType.REJECT:
        proposal.status = ProposalStatus.REJECTED
    else:
        proposal.status = ProposalStatus.REVIEWED
    db.add(proposal)

    # 6. Audit Logging
    audit_log = AuditLog(
        merchant_id=proposal.merchant_id,
        agent_id=proposal.agent_id,
        proposal_id=proposal.id,
        decision_id=shield_decision.id,
        event_type=AuditEventType.SHIELD_DECISION_CREATED,
        action="SHIELD_DECISION_CREATED",
        details={
            "decision": decision.value,
            "final_action": final_action,
            "final_action_parameters": final_params,
            "requires_human_review": requires_human_review,
            "reason_summary": reason
        }
    )
    db.add(audit_log)
    
    db.commit()
    db.refresh(shield_decision)
    return shield_decision
