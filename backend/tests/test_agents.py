from fastapi.testclient import TestClient
from decimal import Decimal
from app.main import app
from app.database.session import SessionLocal
from app.database.models.transaction import Transaction
from app.database.models.customer import Customer
from app.database.models.merchant import Merchant
from app.database.models.agent_proposal import AgentProposal
from app.database.models.audit_log import AuditLog
from app.database.models.enums import TransactionStatus, ProposalStatus, AuditEventType

client = TestClient(app)

def test_fraud_agent_untrusted_device_and_location():
    db = SessionLocal()
    prop_id = None
    try:
        # Fetch suspicious transaction tx_vc_304
        tx = db.query(Transaction).filter(Transaction.external_transaction_id == "tx_vc_304").first()
        assert tx is not None

        # Clean up any existing pending proposals for this transaction to prevent idempotency match
        db.query(AuditLog).filter(AuditLog.proposal_id.in_(
            db.query(AgentProposal.id).filter(AgentProposal.event_id == str(tx.id), AgentProposal.status == ProposalStatus.PENDING)
        )).delete(synchronize_session=False)
        db.query(AgentProposal).filter(AgentProposal.event_id == str(tx.id), AgentProposal.status == ProposalStatus.PENDING).delete(synchronize_session=False)
        db.commit()

        # Execute Fraud agent
        response = client.post("/api/v1/agents/fraud/execute", json={"transaction_id": str(tx.id)})
        assert response.status_code == 201
        data = response.json()
        
        # Verify proposal properties
        assert data["action"] == "STEP_UP_VERIFICATION"
        assert float(data["confidence"]) == 0.88
        assert "NEW_DEVICE" in data["evidence"]
        assert "UNUSUAL_LOCATION" in data["evidence"]
        assert "HIGH_TRANSACTION_VELOCITY" in data["evidence"]

        # Verify proposal is saved in the database
        prop_id = data["proposal_id"]
        prop_db = db.query(AgentProposal).filter(AgentProposal.id == prop_id).first()
        assert prop_db is not None

        # Verify audit log is created
        audit_log = db.query(AuditLog).filter(
            AuditLog.proposal_id == prop_db.id,
            AuditLog.event_type == AuditEventType.AGENT_PROPOSAL_CREATED
        ).first()
        assert audit_log is not None
    finally:
        if prop_id:
            db.query(AuditLog).filter(AuditLog.proposal_id == prop_id).delete(synchronize_session=False)
            db.query(AgentProposal).filter(AgentProposal.id == prop_id).delete(synchronize_session=False)
            db.commit()
        db.close()

def test_fraud_agent_clean_transaction():
    db = SessionLocal()
    prop_id = None
    try:
        tx = db.query(Transaction).filter(Transaction.external_transaction_id == "tx_vc_101").first()
        assert tx is not None

        # Clean up any existing pending proposals for this transaction to prevent idempotency match
        db.query(AuditLog).filter(AuditLog.proposal_id.in_(
            db.query(AgentProposal.id).filter(AgentProposal.event_id == str(tx.id), AgentProposal.status == ProposalStatus.PENDING)
        )).delete(synchronize_session=False)
        db.query(AgentProposal).filter(AgentProposal.event_id == str(tx.id), AgentProposal.status == ProposalStatus.PENDING).delete(synchronize_session=False)
        db.commit()

        # Execute Fraud agent
        response = client.post("/api/v1/agents/fraud/execute", json={"transaction_id": str(tx.id)})
        assert response.status_code == 201
        data = response.json()
        assert data["action"] == "ALLOW_TRANSACTION"
        assert float(data["confidence"]) == 0.95
        assert len(data["evidence"]) == 0

        prop_id = data["proposal_id"]
    finally:
        if prop_id:
            db.query(AuditLog).filter(AuditLog.proposal_id == prop_id).delete(synchronize_session=False)
            db.query(AgentProposal).filter(AgentProposal.id == prop_id).delete(synchronize_session=False)
            db.commit()
        db.close()

def test_recovery_agent_failed_transaction():
    db = SessionLocal()
    prop_id = None
    try:
        # Fetch seeded failed transaction tx_vc_302
        tx = db.query(Transaction).filter(Transaction.external_transaction_id == "tx_vc_302").first()
        assert tx is not None

        # Clean up ALL existing proposals (including seeded ones) to reset retry state for this test
        db.query(AuditLog).filter(AuditLog.proposal_id.in_(
            db.query(AgentProposal.id).filter(AgentProposal.event_id == str(tx.id))
        )).delete(synchronize_session=False)
        db.query(AgentProposal).filter(AgentProposal.event_id == str(tx.id)).delete(synchronize_session=False)
        db.commit()

        # Execute Recovery Agent
        response = client.post("/api/v1/agents/recovery/execute", json={"transaction_id": str(tx.id)})
        assert response.status_code == 201
        data = response.json()

        # Check wait and retry proposal
        assert data["action"] == "WAIT_AND_RETRY"
        assert data["action_parameters"]["wait_hours"] == 24
        assert "CARD_DECLINED_INSUFFICIENT_FUNDS" in data["evidence"]

        prop_id = data["proposal_id"]
    finally:
        if prop_id:
            db.query(AuditLog).filter(AuditLog.proposal_id == prop_id).delete(synchronize_session=False)
            db.query(AgentProposal).filter(AgentProposal.id == prop_id).delete(synchronize_session=False)
            db.commit()
        db.close()

def test_growth_agent_discount_scenario():
    db = SessionLocal()
    prop_id = None
    try:
        customer = db.query(Customer).filter(Customer.external_customer_id == "cust_sf_001").first()
        assert customer is not None

        sf = db.query(Merchant).filter(Merchant.slug == "scribeflow-premium").first()
        assert sf is not None

        # Clean up any existing pending proposals for this customer to prevent idempotency match
        db.query(AuditLog).filter(AuditLog.proposal_id.in_(
            db.query(AgentProposal.id).filter(AgentProposal.event_id == str(customer.id), AgentProposal.status == ProposalStatus.PENDING)
        )).delete(synchronize_session=False)
        db.query(AgentProposal).filter(AgentProposal.event_id == str(customer.id), AgentProposal.status == ProposalStatus.PENDING).delete(synchronize_session=False)
        db.commit()

        # Execute Growth Agent on ScribeFlow & Rohan Das
        response = client.post("/api/v1/agents/growth/execute", json={
            "merchant_id": str(sf.id),
            "customer_id": str(customer.id)
        })
        assert response.status_code == 201
        data = response.json()

        assert data["action"] == "APPLY_DISCOUNT"
        assert data["action_parameters"]["discount_percent"] == 25
        assert "CART_ABANDONMENT_HIGH_VALUE" in data["evidence"]

        prop_id = data["proposal_id"]
    finally:
        if prop_id:
            db.query(AuditLog).filter(AuditLog.proposal_id == prop_id).delete(synchronize_session=False)
            db.query(AgentProposal).filter(AgentProposal.id == prop_id).delete(synchronize_session=False)
            db.commit()
        db.close()

def test_idempotency_prevention():
    db = SessionLocal()
    prop_id = None
    try:
        tx = db.query(Transaction).filter(Transaction.external_transaction_id == "tx_vc_304").first()
        assert tx is not None

        # Clean up any existing pending proposals for this transaction
        db.query(AuditLog).filter(AuditLog.proposal_id.in_(
            db.query(AgentProposal.id).filter(AgentProposal.event_id == str(tx.id), AgentProposal.status == ProposalStatus.PENDING)
        )).delete(synchronize_session=False)
        db.query(AgentProposal).filter(AgentProposal.event_id == str(tx.id), AgentProposal.status == ProposalStatus.PENDING).delete(synchronize_session=False)
        db.commit()

        # First execution
        response1 = client.post("/api/v1/agents/fraud/execute", json={"transaction_id": str(tx.id)})
        assert response1.status_code == 201
        prop_id = response1.json()["proposal_id"]

        # Second execution immediately
        response2 = client.post("/api/v1/agents/fraud/execute", json={"transaction_id": str(tx.id)})
        assert response2.status_code == 201
        id2 = response2.json()["proposal_id"]

        # Assert same proposal is returned
        assert prop_id == id2
    finally:
        if prop_id:
            db.query(AuditLog).filter(AuditLog.proposal_id == prop_id).delete(synchronize_session=False)
            db.query(AgentProposal).filter(AgentProposal.id == prop_id).delete(synchronize_session=False)
            db.commit()
        db.close()

def test_validation_errors():
    fake_id = "00000000-0000-0000-0000-000000000000"
    response = client.post("/api/v1/agents/fraud/execute", json={"transaction_id": fake_id})
    assert response.status_code == 404

    db = SessionLocal()
    try:
        tx_success = db.query(Transaction).filter(Transaction.external_transaction_id == "tx_vc_101").first()
        assert tx_success is not None
        response = client.post("/api/v1/agents/recovery/execute", json={"transaction_id": str(tx_success.id)})
        assert response.status_code == 422
        assert "not eligible for recovery" in response.json()["detail"]
    finally:
        db.close()

    db = SessionLocal()
    try:
        m_np = db.query(Merchant).filter(Merchant.slug == "novapixel-assets").first()
        cust_vc = db.query(Customer).filter(Customer.external_customer_id == "cust_vc_001").first()
        assert m_np is not None
        assert cust_vc is not None

        response = client.post("/api/v1/agents/growth/execute", json={
            "merchant_id": str(m_np.id),
            "customer_id": str(cust_vc.id)
        })
        assert response.status_code == 422
        assert "does not belong to the specified merchant" in response.json()["detail"]
    finally:
        db.close()
