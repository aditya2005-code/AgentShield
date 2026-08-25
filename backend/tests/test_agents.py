from fastapi.testclient import TestClient
from unittest.mock import patch
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

@patch("app.llm.provider.LLMProvider.generate_structured_output")
def test_fraud_agent_untrusted_device_and_location(mock_gen):
    mock_gen.return_value = {
        "proposed_action": "STEP_UP_VERIFICATION",
        "action_parameters": None,
        "confidence": 0.88,
        "evidence": ["NEW_DEVICE", "UNUSUAL_LOCATION", "HIGH_TRANSACTION_VELOCITY"],
        "reason_summary": "Kabir Singh transaction occurred at anomalous location (Moscow, Russia) using untrusted device.",
        "financial_impact": "MEDIUM",
        "customer_impact": "MEDIUM"
    }

    db = SessionLocal()
    prop_id = None
    try:
        # Fetch suspicious transaction tx_vc_304
        tx = db.query(Transaction).filter(Transaction.external_transaction_id == "tx_vc_304").first()
        assert tx is not None

        # Clean up any existing pending proposals for this transaction
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

@patch("app.llm.provider.LLMProvider.generate_structured_output")
def test_fraud_agent_clean_transaction(mock_gen):
    mock_gen.return_value = {
        "proposed_action": "ALLOW_TRANSACTION",
        "action_parameters": None,
        "confidence": 0.95,
        "evidence": [],
        "reason_summary": "No anomalous risk signals detected. Allowing transaction.",
        "financial_impact": "LOW",
        "customer_impact": "LOW"
    }

    db = SessionLocal()
    prop_id = None
    try:
        tx = db.query(Transaction).filter(Transaction.external_transaction_id == "tx_vc_101").first()
        assert tx is not None

        # Clean up any existing pending proposals for this transaction
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

@patch("app.llm.provider.LLMProvider.generate_structured_output")
def test_recovery_agent_failed_transaction(mock_gen):
    mock_gen.return_value = {
        "proposed_action": "WAIT_AND_RETRY",
        "action_parameters": {"wait_hours": 24},
        "confidence": 0.82,
        "evidence": ["CARD_DECLINED_INSUFFICIENT_FUNDS"],
        "reason_summary": "Credit Card declined for insufficient funds. Proposing temporary wait and retry sequence.",
        "financial_impact": "LOW",
        "customer_impact": "LOW"
    }

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

@patch("app.llm.provider.LLMProvider.generate_structured_output")
def test_growth_agent_discount_scenario(mock_gen):
    mock_gen.return_value = {
        "proposed_action": "APPLY_DISCOUNT",
        "action_parameters": {"discount_percent": 25},
        "confidence": 0.85,
        "evidence": ["CART_ABANDONMENT_HIGH_VALUE"],
        "reason_summary": "High-value cart abandoned by customer. Proposing 25% recovery discount promotion.",
        "financial_impact": "MEDIUM",
        "customer_impact": "LOW"
    }

    db = SessionLocal()
    prop_id = None
    try:
        customer = db.query(Customer).filter(Customer.external_customer_id == "cust_sf_001").first()
        assert customer is not None

        sf = db.query(Merchant).filter(Merchant.slug == "scribeflow-premium").first()
        assert sf is not None

        # Clean up any existing pending proposals for this customer
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

@patch("app.llm.provider.LLMProvider.generate_structured_output")
def test_idempotency_prevention(mock_gen):
    mock_gen.return_value = {
        "proposed_action": "STEP_UP_VERIFICATION",
        "action_parameters": None,
        "confidence": 0.88,
        "evidence": ["NEW_DEVICE", "UNUSUAL_LOCATION"],
        "reason_summary": "Suspicious transaction context.",
        "financial_impact": "MEDIUM",
        "customer_impact": "MEDIUM"
    }

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

@patch("app.llm.provider.LLMProvider.generate_structured_output")
def test_validation_errors_gemini_failure(mock_gen):
    # Simulate a validation failure, timeout, or structure error from Gemini
    mock_gen.side_effect = ValueError("Gemini returned invalid action code")

    db = SessionLocal()
    try:
        tx = db.query(Transaction).filter(Transaction.external_transaction_id == "tx_vc_304").first()
        assert tx is not None

        # Clean up any existing pending proposals for this transaction to verify no partial write
        db.query(AuditLog).filter(AuditLog.proposal_id.in_(
            db.query(AgentProposal.id).filter(AgentProposal.event_id == str(tx.id), AgentProposal.status == ProposalStatus.PENDING)
        )).delete(synchronize_session=False)
        db.query(AgentProposal).filter(AgentProposal.event_id == str(tx.id), AgentProposal.status == ProposalStatus.PENDING).delete(synchronize_session=False)
        db.commit()

        # Count audit logs before
        count_before = db.query(AuditLog).count()

        # Call endpoint - should return controlled 422 error
        response = client.post("/api/v1/agents/fraud/execute", json={"transaction_id": str(tx.id)})
        assert response.status_code == 422
        assert "Gemini returned invalid action code" in response.json()["detail"]

        # Assert no new pending proposal was persisted
        props = db.query(AgentProposal).filter(
            AgentProposal.event_id == str(tx.id),
            AgentProposal.status == ProposalStatus.PENDING
        ).all()
        assert len(props) == 0

        # Assert no new audit log was generated
        count_after = db.query(AuditLog).count()
        assert count_after == count_before
    finally:
        db.close()


@patch("app.llm.provider.LLMProvider.generate_structured_output")
@patch("app.ml.inference.service.FraudPredictionService.predict_transaction")
def test_fraud_agent_ml_integration_high_risk(mock_predict, mock_gen):
    """Test that Fraud Agent queries prediction service, passes correct features, and propagates HIGH risk."""
    from app.ml.inference.service import FraudPredictionResult
    from app.ml.inference.risk_classifier import FraudRiskLevel
    
    mock_predict.return_value = FraudPredictionResult(
        fraud_probability=0.87,
        probability=0.87,
        risk_level=FraudRiskLevel.HIGH,
        is_fraud=True,
        threshold=0.25,
        model_version="1.0.0",
        model_name="HistGradientBoostingClassifier"
    )
    
    mock_gen.return_value = {
        "proposed_action": "BLOCK_TRANSACTION",
        "action_parameters": None,
        "confidence": 0.95,
        "evidence": ["HIGH_ML_FRAUD_RISK", "UNUSUAL_LOCATION"],
        "reason_summary": "Transaction flagged with high ML risk score.",
        "financial_impact": "MEDIUM",
        "customer_impact": "LOW"
    }

    db = SessionLocal()
    try:
        tx = db.query(Transaction).filter(Transaction.external_transaction_id == "tx_vc_304").first()
        assert tx is not None
        
        from app.agents.fraud.agent import FraudAgent
        agent = FraudAgent()
        proposal = agent.execute("TRANSACTION", str(tx.id), str(tx.merchant_id), db)
        
        mock_predict.assert_called_once()
        passed_features = mock_predict.call_args[0][0]
        assert passed_features["Amount"] == 120000.0
        assert passed_features["Merchant_Category"] == "Electronics"
        assert passed_features["Device_Type"] == "Web_Browser"
        assert passed_features["Distance_from_Home"] == 4.8088
        assert passed_features["IP_Risk_Score"] == 0.85
        assert passed_features["Avg_Spending_Habit"] == 55000.0
        
        prompt_passed = mock_gen.call_args[0][0]
        assert "[FRAUD ML EVIDENCE]" in prompt_passed
        assert "Fraud probability: 0.8700" in prompt_passed
        assert "Fraud risk level: HIGH" in prompt_passed
        assert "Do not alter, override, or recalculate the probability" in prompt_passed

        assert proposal.action_parameters["fraud_probability"] == 0.87
        assert proposal.action_parameters["fraud_risk_level"] == "HIGH"
        assert proposal.action_parameters["ml_model_version"] == "1.0.0"
        
    finally:
        db.close()


@patch("app.llm.provider.LLMProvider.generate_structured_output")
@patch("app.ml.inference.service.FraudPredictionService.predict_transaction")
def test_fraud_agent_ml_integration_low_risk(mock_predict, mock_gen):
    """Test that Fraud Agent correctly handles and injects LOW risk prediction."""
    from app.ml.inference.service import FraudPredictionResult
    from app.ml.inference.risk_classifier import FraudRiskLevel
    
    mock_predict.return_value = FraudPredictionResult(
        fraud_probability=0.02,
        probability=0.02,
        risk_level=FraudRiskLevel.LOW,
        is_fraud=False,
        threshold=0.25,
        model_version="1.0.0",
        model_name="HistGradientBoostingClassifier"
    )
    
    mock_gen.return_value = {
        "proposed_action": "ALLOW_TRANSACTION",
        "action_parameters": None,
        "confidence": 0.99,
        "evidence": [],
        "reason_summary": "Transaction looks clean.",
        "financial_impact": "LOW",
        "customer_impact": "LOW"
    }

    db = SessionLocal()
    try:
        tx = db.query(Transaction).filter(Transaction.external_transaction_id == "tx_vc_103").first()
        
        from app.agents.fraud.agent import FraudAgent
        agent = FraudAgent()
        proposal = agent.execute("TRANSACTION", str(tx.id), str(tx.merchant_id), db)
        
        prompt_passed = mock_gen.call_args[0][0]
        assert "[FRAUD ML EVIDENCE]" in prompt_passed
        assert "Fraud probability: 0.0200" in prompt_passed
        assert "Fraud risk level: LOW" in prompt_passed
        assert "Model classification: CLEAN" in prompt_passed

        assert proposal.action_parameters["fraud_probability"] == 0.02
        assert proposal.action_parameters["fraud_risk_level"] == "LOW"
        
    finally:
        db.close()


@patch("app.llm.provider.LLMProvider.generate_structured_output")
@patch("app.ml.inference.service.FraudPredictionService.predict_transaction")
def test_fraud_agent_ml_degraded_mode(mock_predict, mock_gen):
    """Test that Fraud Agent executes in degraded mode when service prediction fails."""
    mock_predict.side_effect = Exception("Prediction service crash")
    
    mock_gen.return_value = {
        "proposed_action": "ALLOW_TRANSACTION",
        "action_parameters": None,
        "confidence": 0.88,
        "evidence": [],
        "reason_summary": "Degraded mode reasoning",
        "financial_impact": "LOW",
        "customer_impact": "LOW"
    }

    db = SessionLocal()
    try:
        tx = db.query(Transaction).filter(Transaction.external_transaction_id == "tx_vc_101").first()
        
        from app.agents.fraud.agent import FraudAgent
        agent = FraudAgent()
        proposal = agent.execute("TRANSACTION", str(tx.id), str(tx.merchant_id), db)
        
        prompt_passed = mock_gen.call_args[0][0]
        assert "ML fraud prediction signal is currently UNAVAILABLE" in prompt_passed
        assert proposal.action_parameters["ml_signal_available"] is False
        
    finally:
        db.close()

