import uuid
from decimal import Decimal
from fastapi.testclient import TestClient
from app.main import app
from app.database.session import SessionLocal
from app.database.models.agent import Agent
from app.database.models.merchant import Merchant
from app.database.models.agent_proposal import AgentProposal
from app.database.models.shield_decision import ShieldDecision
from app.database.models.audit_log import AuditLog
from app.database.models.enums import AgentType, ProposalStatus, ShieldDecisionType, ImpactLevel, AuditEventType

client = TestClient(app)

def test_agentshield_authorization_checks():
    db = SessionLocal()
    proposal_ids = []
    try:
        # Load agents and merchant
        fraud_agent = db.query(Agent).filter(Agent.agent_type == AgentType.FRAUD).first()
        recovery_agent = db.query(Agent).filter(Agent.agent_type == AgentType.RECOVERY).first()
        growth_agent = db.query(Agent).filter(Agent.agent_type == AgentType.GROWTH).first()
        merchant = db.query(Merchant).filter(Merchant.slug == "velocart-electronics").first()

        assert fraud_agent is not None
        assert recovery_agent is not None
        assert growth_agent is not None
        assert merchant is not None

        # Case 1: Fraud Agent proposes a valid action (e.g., STEP_UP_VERIFICATION) -> Should NOT fail auth check
        p1 = AgentProposal(
            agent_id=fraud_agent.id,
            merchant_id=merchant.id,
            event_type="TRANSACTION",
            event_id=str(uuid.uuid4()),
            action="STEP_UP_VERIFICATION",
            action_parameters=None,
            confidence=Decimal("0.85"),
            financial_impact=ImpactLevel.MEDIUM,
            customer_impact=ImpactLevel.MEDIUM,
            evidence=["NEW_DEVICE"],
            reason_summary="Suspicious login pattern detected",
            status=ProposalStatus.PENDING
        )
        db.add(p1)
        db.commit()
        proposal_ids.append(p1.id)

        response = client.post(f"/api/v1/agentshield/evaluate/{p1.id}")
        assert response.status_code == 201
        data = response.json()
        assert data["decision"] != "REJECT"
        # Check authorization passed
        auth_check = next(c for c in data["checks"] if c["check"] == "authorization")
        assert auth_check["status"] == "PASSED"

        # Case 2: Fraud Agent proposes an invalid action (e.g., APPLY_DISCOUNT) -> Should REJECT
        p2 = AgentProposal(
            agent_id=fraud_agent.id,
            merchant_id=merchant.id,
            event_type="TRANSACTION",
            event_id=str(uuid.uuid4()),
            action="APPLY_DISCOUNT",
            action_parameters={"discount_percent": 15},
            confidence=Decimal("0.90"),
            financial_impact=ImpactLevel.LOW,
            customer_impact=ImpactLevel.LOW,
            evidence=["CLEAN_HISTORY"],
            reason_summary="Giving discount from fraud agent",
            status=ProposalStatus.PENDING
        )
        db.add(p2)
        db.commit()
        proposal_ids.append(p2.id)

        response = client.post(f"/api/v1/agentshield/evaluate/{p2.id}")
        assert response.status_code == 201
        data = response.json()
        assert data["decision"] == "REJECT"
        auth_check = next(c for c in data["checks"] if c["check"] == "authorization")
        assert auth_check["status"] == "FAILED"

        # Case 3: Recovery Agent proposes invalid action ALLOW_TRANSACTION -> Should REJECT
        p3 = AgentProposal(
            agent_id=recovery_agent.id,
            merchant_id=merchant.id,
            event_type="PAYMENT_FAILURE",
            event_id=str(uuid.uuid4()),
            action="ALLOW_TRANSACTION",
            action_parameters=None,
            confidence=Decimal("0.80"),
            financial_impact=ImpactLevel.LOW,
            customer_impact=ImpactLevel.LOW,
            evidence=["RETRY_FAIL"],
            reason_summary="Allow transaction from recovery agent",
            status=ProposalStatus.PENDING
        )
        db.add(p3)
        db.commit()
        proposal_ids.append(p3.id)

        response = client.post(f"/api/v1/agentshield/evaluate/{p3.id}")
        assert response.status_code == 201
        assert response.json()["decision"] == "REJECT"

        # Case 4: Growth Agent proposes invalid action BLOCK_TRANSACTION -> Should REJECT
        p4 = AgentProposal(
            agent_id=growth_agent.id,
            merchant_id=merchant.id,
            event_type="GROWTH_OPPORTUNITY",
            event_id=str(uuid.uuid4()),
            action="BLOCK_TRANSACTION",
            action_parameters=None,
            confidence=Decimal("0.95"),
            financial_impact=ImpactLevel.MEDIUM,
            customer_impact=ImpactLevel.HIGH,
            evidence=[],
            reason_summary="Block customer from growth agent",
            status=ProposalStatus.PENDING
        )
        db.add(p4)
        db.commit()
        proposal_ids.append(p4.id)

        response = client.post(f"/api/v1/agentshield/evaluate/{p4.id}")
        assert response.status_code == 201
        assert response.json()["decision"] == "REJECT"

    finally:
        for p_id in proposal_ids:
            db.query(AuditLog).filter(AuditLog.proposal_id == p_id).delete()
            db.query(ShieldDecision).filter(ShieldDecision.proposal_id == p_id).delete()
            db.query(AgentProposal).filter(AgentProposal.id == p_id).delete()
        db.commit()
        db.close()

def test_agentshield_merchant_policy_checks():
    db = SessionLocal()
    proposal_ids = []
    try:
        growth_agent = db.query(Agent).filter(Agent.agent_type == AgentType.GROWTH).first()
        merchant = db.query(Merchant).filter(Merchant.slug == "velocart-electronics").first()

        assert growth_agent is not None
        assert merchant is not None

        # Case 1: Discount within policy (e.g., 5% discount, policy is max 10%) -> Should PASS
        p1 = AgentProposal(
            agent_id=growth_agent.id,
            merchant_id=merchant.id,
            event_type="GROWTH_OPPORTUNITY",
            event_id=str(uuid.uuid4()),
            action="APPLY_DISCOUNT",
            action_parameters={"discount_percent": 5},
            confidence=Decimal("0.85"),
            financial_impact=ImpactLevel.LOW,
            customer_impact=ImpactLevel.LOW,
            evidence=["LOYAL_CUSTOMER"],
            reason_summary="Regular loyalty discount",
            status=ProposalStatus.PENDING
        )
        db.add(p1)
        db.commit()
        proposal_ids.append(p1.id)

        response = client.post(f"/api/v1/agentshield/evaluate/{p1.id}")
        assert response.status_code == 201
        data = response.json()
        assert data["decision"] == "APPROVE"
        assert data["final_action_parameters"]["discount_percent"] == 5

        # Case 2: Discount exceeding policy (e.g., 25% discount) -> Should MODIFY to 10%
        p2 = AgentProposal(
            agent_id=growth_agent.id,
            merchant_id=merchant.id,
            event_type="GROWTH_OPPORTUNITY",
            event_id=str(uuid.uuid4()),
            action="APPLY_DISCOUNT",
            action_parameters={"discount_percent": 25},
            confidence=Decimal("0.85"),
            financial_impact=ImpactLevel.LOW,
            customer_impact=ImpactLevel.LOW,
            evidence=["CART_ABANDONMENT_HIGH_VALUE"],
            reason_summary="High incentive cart recovery discount",
            status=ProposalStatus.PENDING
        )
        db.add(p2)
        db.commit()
        proposal_ids.append(p2.id)

        response = client.post(f"/api/v1/agentshield/evaluate/{p2.id}")
        assert response.status_code == 201
        data = response.json()
        
        # Verify ShieldDecision is MODIFY
        assert data["decision"] == "MODIFY"
        # Verify original parameters are preserved
        assert data["original_parameters"]["discount_percent"] == 25
        # Verify final parameters are overridden to 10%
        assert data["final_action_parameters"]["discount_percent"] == 10
        # Verify modifications record what we modified from
        assert data["modifications"]["discount_percent"] == 25
        # Verify human review is false (auto-modified)
        assert data["requires_human_review"] is False

    finally:
        for p_id in proposal_ids:
            db.query(AuditLog).filter(AuditLog.proposal_id == p_id).delete()
            db.query(ShieldDecision).filter(ShieldDecision.proposal_id == p_id).delete()
            db.query(AgentProposal).filter(AgentProposal.id == p_id).delete()
        db.commit()
        db.close()

def test_agentshield_risk_safety_checks():
    db = SessionLocal()
    proposal_ids = []
    try:
        fraud_agent = db.query(Agent).filter(Agent.agent_type == AgentType.FRAUD).first()
        merchant = db.query(Merchant).filter(Merchant.slug == "velocart-electronics").first()

        assert fraud_agent is not None
        assert merchant is not None

        # Case 1: Safe high confidence proposal -> Should APPROVE
        p1 = AgentProposal(
            agent_id=fraud_agent.id,
            merchant_id=merchant.id,
            event_type="TRANSACTION",
            event_id=str(uuid.uuid4()),
            action="ALLOW_TRANSACTION",
            action_parameters=None,
            confidence=Decimal("0.95"),
            financial_impact=ImpactLevel.LOW,
            customer_impact=ImpactLevel.LOW,
            evidence=[],
            reason_summary="Clean risk profile",
            status=ProposalStatus.PENDING
        )
        db.add(p1)
        db.commit()
        proposal_ids.append(p1.id)

        response = client.post(f"/api/v1/agentshield/evaluate/{p1.id}")
        assert response.status_code == 201
        assert response.json()["decision"] == "APPROVE"

        # Case 2: Low confidence high impact proposal -> Should ESCALATE
        p2 = AgentProposal(
            agent_id=fraud_agent.id,
            merchant_id=merchant.id,
            event_type="TRANSACTION",
            event_id=str(uuid.uuid4()),
            action="STEP_UP_VERIFICATION",
            action_parameters=None,
            confidence=Decimal("0.58"),
            financial_impact=ImpactLevel.HIGH,
            customer_impact=ImpactLevel.MEDIUM,
            evidence=["NEW_DEVICE"],
            reason_summary="Low confidence flag",
            status=ProposalStatus.PENDING
        )
        db.add(p2)
        db.commit()
        proposal_ids.append(p2.id)

        response = client.post(f"/api/v1/agentshield/evaluate/{p2.id}")
        assert response.status_code == 201
        data = response.json()
        assert data["decision"] == "ESCALATE"
        assert data["requires_human_review"] is True

        # Case 3: Missing evidence for security block -> Should REJECT
        p3 = AgentProposal(
            agent_id=fraud_agent.id,
            merchant_id=merchant.id,
            event_type="TRANSACTION",
            event_id=str(uuid.uuid4()),
            action="BLOCK_TRANSACTION",
            action_parameters=None,
            confidence=Decimal("0.90"),
            financial_impact=ImpactLevel.HIGH,
            customer_impact=ImpactLevel.HIGH,
            evidence=[],  # Empty evidence for block action!
            reason_summary="Blocking transaction without saying why",
            status=ProposalStatus.PENDING
        )
        db.add(p3)
        db.commit()
        proposal_ids.append(p3.id)

        response = client.post(f"/api/v1/agentshield/evaluate/{p3.id}")
        assert response.status_code == 201
        assert response.json()["decision"] == "REJECT"

    finally:
        for p_id in proposal_ids:
            db.query(AuditLog).filter(AuditLog.proposal_id == p_id).delete()
            db.query(ShieldDecision).filter(ShieldDecision.proposal_id == p_id).delete()
            db.query(AgentProposal).filter(AgentProposal.id == p_id).delete()
        db.commit()
        db.close()

def test_agentshield_idempotency_checks():
    db = SessionLocal()
    proposal_ids = []
    try:
        growth_agent = db.query(Agent).filter(Agent.agent_type == AgentType.GROWTH).first()
        merchant = db.query(Merchant).filter(Merchant.slug == "velocart-electronics").first()

        assert growth_agent is not None
        assert merchant is not None

        p1 = AgentProposal(
            agent_id=growth_agent.id,
            merchant_id=merchant.id,
            event_type="GROWTH_OPPORTUNITY",
            event_id=str(uuid.uuid4()),
            action="SEND_PROMOTION",
            action_parameters={"promo_code": "RETENTION_10"},
            confidence=Decimal("0.80"),
            financial_impact=ImpactLevel.LOW,
            customer_impact=ImpactLevel.LOW,
            evidence=["LOYAL_CUSTOMER"],
            reason_summary="Send retention promo code",
            status=ProposalStatus.PENDING
        )
        db.add(p1)
        db.commit()
        proposal_ids.append(p1.id)

        # First evaluation
        response1 = client.post(f"/api/v1/agentshield/evaluate/{p1.id}")
        assert response1.status_code == 201
        data1 = response1.json()

        # Count decisions in database for this proposal
        count_first = db.query(ShieldDecision).filter(ShieldDecision.proposal_id == p1.id).count()
        assert count_first == 1

        # Second evaluation immediately
        response2 = client.post(f"/api/v1/agentshield/evaluate/{p1.id}")
        assert response2.status_code in (200, 201)
        data2 = response2.json()

        # Assert no duplicate decision was inserted
        count_second = db.query(ShieldDecision).filter(ShieldDecision.proposal_id == p1.id).count()
        assert count_second == 1

        # Check reason matches
        assert data1["reason_summary"] == data2["reason_summary"]

    finally:
        for p_id in proposal_ids:
            db.query(AuditLog).filter(AuditLog.proposal_id == p_id).delete()
            db.query(ShieldDecision).filter(ShieldDecision.proposal_id == p_id).delete()
            db.query(AgentProposal).filter(AgentProposal.id == p_id).delete()
        db.commit()
        db.close()

def test_agentshield_persistence_lifecycle():
    db = SessionLocal()
    proposal_ids = []
    try:
        growth_agent = db.query(Agent).filter(Agent.agent_type == AgentType.GROWTH).first()
        merchant = db.query(Merchant).filter(Merchant.slug == "velocart-electronics").first()

        p1 = AgentProposal(
            agent_id=growth_agent.id,
            merchant_id=merchant.id,
            event_type="GROWTH_OPPORTUNITY",
            event_id=str(uuid.uuid4()),
            action="SEND_PROMOTION",
            action_parameters={"promo_code": "RETENTION_10"},
            confidence=Decimal("0.80"),
            financial_impact=ImpactLevel.LOW,
            customer_impact=ImpactLevel.LOW,
            evidence=["LOYAL_CUSTOMER"],
            reason_summary="Send retention promo code",
            status=ProposalStatus.PENDING
        )
        db.add(p1)
        db.commit()
        proposal_ids.append(p1.id)

        # Execute evaluation
        response = client.post(f"/api/v1/agentshield/evaluate/{p1.id}")
        assert response.status_code == 201
        
        # 1. Assert ShieldDecision is saved
        decision_db = db.query(ShieldDecision).filter(ShieldDecision.proposal_id == p1.id).first()
        assert decision_db is not None
        assert decision_db.decision == ShieldDecisionType.APPROVE

        # 2. Assert Proposal status is updated to REVIEWED
        db.refresh(p1)
        assert p1.status == ProposalStatus.REVIEWED

        # 3. Assert Audit log is created
        audit_log = db.query(AuditLog).filter(
            AuditLog.proposal_id == p1.id,
            AuditLog.event_type == AuditEventType.SHIELD_DECISION_CREATED
        ).first()
        assert audit_log is not None
        assert audit_log.details["decision"] == "APPROVE"

    finally:
        for p_id in proposal_ids:
            db.query(AuditLog).filter(AuditLog.proposal_id == p_id).delete()
            db.query(ShieldDecision).filter(ShieldDecision.proposal_id == p_id).delete()
            db.query(AgentProposal).filter(AgentProposal.id == p_id).delete()
        db.commit()
        db.close()
