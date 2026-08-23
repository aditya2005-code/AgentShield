import uuid
from typing import List
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from app.database.session import get_db
from app.schemas.agent import AgentResponse
from app.services import agent_service

router = APIRouter(prefix="/agents", tags=["Agents"])

@router.get("", response_model=List[AgentResponse], summary="Retrieve all agents")
def read_agents(db: Session = Depends(get_db)):
    """
    Fetch all agents defined in the system.
    """
    return agent_service.get_agents(db)

@router.get("/{agent_id}", response_model=AgentResponse, summary="Retrieve a single agent by ID")
def read_agent(agent_id: uuid.UUID, db: Session = Depends(get_db)):
    """
    Fetch a single agent by its unique UUID.
    """
    agent = agent_service.get_agent_by_id(db, agent_id)
    if not agent:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Agent with ID {agent_id} not found"
        )
    return agent

# Part 8 Execution Routes
from app.agents.schemas import FraudExecutionRequest, RecoveryExecutionRequest, GrowthExecutionRequest
from app.agents.router import execute_agent
from app.schemas.action_proposal import ActionProposalResponse
from app.database.models.transaction import Transaction
from app.database.models.customer import Customer
from app.database.models.merchant import Merchant
from app.database.models.agent import Agent
from app.database.models.agent_proposal import AgentProposal
from app.database.models.audit_log import AuditLog
from app.database.models.enums import AgentType, ProposalStatus, AuditEventType, TransactionStatus

@router.post("/fraud/execute", response_model=ActionProposalResponse, status_code=status.HTTP_201_CREATED, summary="Execute Fraud Detection Agent")
def execute_fraud_agent(payload: FraudExecutionRequest, db: Session = Depends(get_db)):
    """
    Execute the Fraud Detection Agent for a specific transaction.
    """
    # 1. Validation
    tx = db.query(Transaction).filter(Transaction.id == payload.transaction_id).first()
    if not tx:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Transaction not found.")
    
    merchant = db.query(Merchant).filter(Merchant.id == tx.merchant_id).first()
    if not merchant:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Merchant associated with transaction not found.")

    agent = db.query(Agent).filter(Agent.agent_type == AgentType.FRAUD).first()
    if not agent:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Fraud Agent is not registered in system.")

    # 2. Idempotency Check
    existing = db.query(AgentProposal).filter(
        AgentProposal.agent_id == agent.id,
        AgentProposal.event_type == "TRANSACTION",
        AgentProposal.event_id == str(payload.transaction_id),
        AgentProposal.status == ProposalStatus.PENDING
    ).first()
    if existing:
        return existing

    # 3. Execution
    try:
        proposal = execute_agent(AgentType.FRAUD, "TRANSACTION", str(payload.transaction_id), str(tx.merchant_id), db)
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=str(e))

    # 4. Persistence
    db.add(proposal)
    db.flush()

    # 5. Audit Logging
    audit_log = AuditLog(
        merchant_id=tx.merchant_id,
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

@router.post("/recovery/execute", response_model=ActionProposalResponse, status_code=status.HTTP_201_CREATED, summary="Execute Payment Recovery Agent")
def execute_recovery_agent(payload: RecoveryExecutionRequest, db: Session = Depends(get_db)):
    """
    Execute the Payment Recovery Agent for a failed transaction.
    """
    # 1. Validation
    tx = db.query(Transaction).filter(Transaction.id == payload.transaction_id).first()
    if not tx:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Transaction not found.")

    if tx.status not in (TransactionStatus.FAILED, TransactionStatus.BLOCKED):
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=f"Transaction is not eligible for recovery (current status: {tx.status.value})."
        )

    agent = db.query(Agent).filter(Agent.agent_type == AgentType.RECOVERY).first()
    if not agent:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Recovery Agent is not registered in system.")

    # 2. Idempotency Check
    existing = db.query(AgentProposal).filter(
        AgentProposal.agent_id == agent.id,
        AgentProposal.event_type == "PAYMENT_FAILURE",
        AgentProposal.event_id == str(payload.transaction_id),
        AgentProposal.status == ProposalStatus.PENDING
    ).first()
    if existing:
        return existing

    # 3. Execution
    try:
        proposal = execute_agent(AgentType.RECOVERY, "PAYMENT_FAILURE", str(payload.transaction_id), str(tx.merchant_id), db)
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=str(e))

    # 4. Persistence
    db.add(proposal)
    db.flush()

    # 5. Audit Logging
    audit_log = AuditLog(
        merchant_id=tx.merchant_id,
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

@router.post("/growth/execute", response_model=ActionProposalResponse, status_code=status.HTTP_201_CREATED, summary="Execute Growth Incentives Agent")
def execute_growth_agent(payload: GrowthExecutionRequest, db: Session = Depends(get_db)):
    """
    Execute the Growth Incentives Agent for a merchant-customer pair.
    """
    # 1. Validation
    merchant = db.query(Merchant).filter(Merchant.id == payload.merchant_id).first()
    if not merchant:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Merchant not found.")

    customer = db.query(Customer).filter(Customer.id == payload.customer_id).first()
    if not customer:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Customer not found.")

    if customer.merchant_id != payload.merchant_id:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="Customer does not belong to the specified merchant."
        )

    agent = db.query(Agent).filter(Agent.agent_type == AgentType.GROWTH).first()
    if not agent:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Growth Agent is not registered in system.")

    # 2. Idempotency Check
    existing = db.query(AgentProposal).filter(
        AgentProposal.agent_id == agent.id,
        AgentProposal.event_type == "GROWTH_OPPORTUNITY",
        AgentProposal.event_id == str(payload.customer_id),
        AgentProposal.status == ProposalStatus.PENDING
    ).first()
    if existing:
        return existing

    # 3. Execution
    try:
        proposal = execute_agent(AgentType.GROWTH, "GROWTH_OPPORTUNITY", str(payload.customer_id), str(payload.merchant_id), db)
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=str(e))

    # 4. Persistence
    db.add(proposal)
    db.flush()

    # 5. Audit Logging
    audit_log = AuditLog(
        merchant_id=payload.merchant_id,
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

