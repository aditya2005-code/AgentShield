import uuid
import pytest
from decimal import Decimal
from unittest.mock import patch, MagicMock
from fastapi.testclient import TestClient

from app.main import app
from app.database.session import SessionLocal
from app.database.models.agent import Agent
from app.database.models.merchant import Merchant
from app.database.models.transaction import Transaction
from app.database.models.agent_proposal import AgentProposal
from app.database.models.shield_decision import ShieldDecision
from app.database.models.audit_log import AuditLog
from app.database.models.enums import AgentType, ProposalStatus, ShieldDecisionType, ImpactLevel
from app.ml.inference.service import FraudPredictionResult
from app.ml.inference.risk_classifier import FraudRiskLevel

client = TestClient(app)

@pytest.fixture
def clean_db():
    db = SessionLocal()
    yield db
    db.close()

@patch("app.llm.provider.LLMProvider.generate_structured_output")
@patch("app.ml.inference.service.FraudPredictionService.predict_transaction")
def test_end_to_end_high_fraud_risk(mock_predict, mock_gen, clean_db):
    """
    Scenario 1: High Fraud Risk E2E Integration
    Verifies that a high-risk transaction invokes the ML prediction, passes through
    the Fraud Agent (including prompt injection), persists ML metrics in proposal.action_parameters,
    and is evaluated by the AgentShield engine to produce a final decision.
    """
    # 1. Mock ML prediction output (HIGH risk)
    mock_predict.return_value = FraudPredictionResult(
        fraud_probability=0.95,
        probability=0.95,
        risk_level=FraudRiskLevel.HIGH,
        is_fraud=True,
        threshold=0.25,
        model_version="1.0.0",
        model_name="HistGradientBoostingClassifier"
    )
    
    # 2. Mock Gemini response to propose BLOCK_TRANSACTION based on high risk context
    mock_gen.return_value = {
        "proposed_action": "BLOCK_TRANSACTION",
        "action_parameters": None,
        "confidence": 0.98,
        "evidence": ["HIGH_ML_FRAUD_RISK", "UNUSUAL_LOCATION"],
        "reason_summary": "High risk ML fraud probability detected with geographic anomaly.",
        "financial_impact": "MEDIUM",
        "customer_impact": "LOW"
    }

    # Fetch suspicious seeded transaction tx_vc_304
    tx = clean_db.query(Transaction).filter(Transaction.external_transaction_id == "tx_vc_304").first()
    assert tx is not None

    # Execute Fraud Agent through HTTP API (which internally calls FraudAgent.execute)
    response = client.post("/api/v1/agents/fraud/execute", json={"transaction_id": str(tx.id)})
    assert response.status_code == 201
    proposal_data = response.json()
    proposal_id = uuid.UUID(proposal_data["proposal_id"])

    # Verify that the ML signals were persisted in the proposal's action_parameters
    proposal = clean_db.query(AgentProposal).filter(AgentProposal.id == proposal_id).first()
    assert proposal is not None
    assert proposal.action_parameters["fraud_probability"] == 0.95
    assert proposal.action_parameters["fraud_risk_level"] == "HIGH"
    assert proposal.action_parameters["ml_model_version"] == "1.0.0"

    # Evaluate the proposal using AgentShield engine endpoint (POST /api/v1/agentshield/evaluate/{proposal_id})
    eval_response = client.post(f"/api/v1/agentshield/evaluate/{proposal_id}")
    assert eval_response.status_code == 201
    eval_data = eval_response.json()

    # The final decision must follow AgentShield deterministic rules
    assert "decision" in eval_data
    
    # Clean up created proposal and its child audit logs
    clean_db.query(AuditLog).filter(AuditLog.proposal_id == proposal_id).delete()
    clean_db.query(ShieldDecision).filter(ShieldDecision.proposal_id == proposal_id).delete()
    clean_db.query(AgentProposal).filter(AgentProposal.id == proposal_id).delete()
    clean_db.commit()


@patch("app.llm.provider.LLMProvider.generate_structured_output")
@patch("app.ml.inference.service.FraudPredictionService.predict_transaction")
def test_end_to_end_low_fraud_risk(mock_predict, mock_gen, clean_db):
    """
    Scenario 2: Low Fraud Risk E2E Integration
    Verifies that a low-risk transaction generates a LOW risk ML signal, the Fraud Agent
    proposes a clean ALLOW_TRANSACTION action, and AgentShield evaluates and approves it.
    """
    mock_predict.return_value = FraudPredictionResult(
        fraud_probability=0.01,
        probability=0.01,
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
        "reason_summary": "Transaction is clean.",
        "financial_impact": "LOW",
        "customer_impact": "LOW"
    }

    tx = clean_db.query(Transaction).filter(Transaction.external_transaction_id == "tx_vc_103").first()
    assert tx is not None

    response = client.post("/api/v1/agents/fraud/execute", json={"transaction_id": str(tx.id)})
    assert response.status_code == 201
    proposal_data = response.json()
    proposal_id = uuid.UUID(proposal_data["proposal_id"])

    # Verify ML signals persisted in DB
    proposal = clean_db.query(AgentProposal).filter(AgentProposal.id == proposal_id).first()
    assert proposal.action_parameters["fraud_probability"] == 0.01
    assert proposal.action_parameters["fraud_risk_level"] == "LOW"

    # Evaluate the proposal using AgentShield
    eval_response = client.post(f"/api/v1/agentshield/evaluate/{proposal_id}")
    assert eval_response.status_code == 201
    eval_data = eval_response.json()
    assert eval_data["decision"] == "APPROVE"

    # Clean up
    clean_db.query(AuditLog).filter(AuditLog.proposal_id == proposal_id).delete()
    clean_db.query(ShieldDecision).filter(ShieldDecision.proposal_id == proposal_id).delete()
    clean_db.query(AgentProposal).filter(AgentProposal.id == proposal_id).delete()
    clean_db.commit()


@patch("app.llm.provider.LLMProvider.generate_structured_output")
@patch("app.ml.inference.service.FraudPredictionService.predict_transaction")
def test_end_to_end_ml_degraded_mode(mock_predict, mock_gen, clean_db):
    """
    Scenario 3: ML Degraded Mode E2E Integration
    Simulates prediction service failure, verifies that the Fraud Agent runs in degraded mode,
    stores ml_signal_available = False, continues prompt formatting, and AgentShield evaluates
    the proposal successfully.
    """
    mock_predict.side_effect = Exception("Predictor artifact missing or failed to load")
    
    mock_gen.return_value = {
        "proposed_action": "ALLOW_TRANSACTION",
        "action_parameters": None,
        "confidence": 0.88,
        "evidence": [],
        "reason_summary": "Executed in degraded mode.",
        "financial_impact": "LOW",
        "customer_impact": "LOW"
    }

    tx = clean_db.query(Transaction).filter(Transaction.external_transaction_id == "tx_vc_101").first()
    assert tx is not None

    # Fraud Agent execution should NOT crash, instead complete successfully (Option B)
    response = client.post("/api/v1/agents/fraud/execute", json={"transaction_id": str(tx.id)})
    assert response.status_code == 201
    proposal_data = response.json()
    proposal_id = uuid.UUID(proposal_data["proposal_id"])

    # Verify that ML Signal availability is recorded as false
    proposal = clean_db.query(AgentProposal).filter(AgentProposal.id == proposal_id).first()
    assert proposal.action_parameters["ml_signal_available"] is False

    # Evaluate the proposal using AgentShield
    eval_response = client.post(f"/api/v1/agentshield/evaluate/{proposal_id}")
    assert eval_response.status_code == 201
    eval_data = eval_response.json()
    assert eval_data["decision"] == "APPROVE"

    # Clean up
    clean_db.query(AuditLog).filter(AuditLog.proposal_id == proposal_id).delete()
    clean_db.query(ShieldDecision).filter(ShieldDecision.proposal_id == proposal_id).delete()
    clean_db.query(AgentProposal).filter(AgentProposal.id == proposal_id).delete()
    clean_db.commit()


@patch("app.llm.provider.LLMProvider.generate_structured_output")
@patch("app.ml.inference.service.FraudPredictionService.predict_transaction")
def test_end_to_end_multi_agent_interaction(mock_predict, mock_gen, clean_db):
    """
    Scenario 4: Multi-Agent Interaction
    Verifies that the Fraud Agent proposal enters the same orchestration flow as
    other agents, can coexist, and the ML probability is not treated as a direct final decision.
    """
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
        "proposed_action": "STEP_UP_VERIFICATION",
        "action_parameters": None,
        "confidence": 0.90,
        "evidence": ["HIGH_ML_FRAUD_RISK"],
        "reason_summary": "Stepping up transaction verification.",
        "financial_impact": "LOW",
        "customer_impact": "LOW"
    }

    tx = clean_db.query(Transaction).filter(Transaction.external_transaction_id == "tx_vc_304").first()
    assert tx is not None

    # Create Fraud Agent proposal
    response = client.post("/api/v1/agents/fraud/execute", json={"transaction_id": str(tx.id)})
    assert response.status_code == 201
    proposal_data = response.json()
    proposal_id = uuid.UUID(proposal_data["proposal_id"])

    # AgentShield should evaluate it using the standard checks
    eval_response = client.post(f"/api/v1/agentshield/evaluate/{proposal_id}")
    assert eval_response.status_code == 201
    eval_data = eval_response.json()
    
    check_names = {c["check"] for c in eval_data["checks"]}
    assert "authorization" in check_names
    assert "merchant_policy" in check_names
    assert "risk_safety" in check_names

    # Clean up
    clean_db.query(AuditLog).filter(AuditLog.proposal_id == proposal_id).delete()
    clean_db.query(ShieldDecision).filter(ShieldDecision.proposal_id == proposal_id).delete()
    clean_db.query(AgentProposal).filter(AgentProposal.id == proposal_id).delete()
    clean_db.commit()


@patch("app.llm.provider.LLMProvider.generate_structured_output")
@patch("app.ml.inference.service.FraudPredictionService.predict_transaction")
def test_end_to_end_auditability(mock_predict, mock_gen, clean_db):
    """
    Scenario 5: Auditability
    Verifies that the entire pipeline execution can be traced from Proposal to ShieldDecision
    and its corresponding AuditLog entry.
    """
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
        "confidence": 0.90,
        "evidence": ["HIGH_ML_FRAUD_RISK"],
        "reason_summary": "Tracing audit log creation.",
        "financial_impact": "MEDIUM",
        "customer_impact": "LOW"
    }

    tx = clean_db.query(Transaction).filter(Transaction.external_transaction_id == "tx_vc_304").first()
    assert tx is not None

    # Step 1: Execute Fraud Agent
    response = client.post("/api/v1/agents/fraud/execute", json={"transaction_id": str(tx.id)})
    proposal_id = uuid.UUID(response.json()["proposal_id"])

    # Step 2: Evaluate using AgentShield
    client.post(f"/api/v1/agentshield/evaluate/{proposal_id}")

    # Step 3: Trace proposal and verify details
    proposal = clean_db.query(AgentProposal).filter(AgentProposal.id == proposal_id).first()
    assert proposal is not None
    assert proposal.action_parameters["fraud_probability"] == 0.87
    assert proposal.action_parameters["fraud_risk_level"] == "HIGH"
    
    # Step 4: Trace ShieldDecision
    decision = clean_db.query(ShieldDecision).filter(ShieldDecision.proposal_id == proposal_id).first()
    assert decision is not None

    # Step 5: Trace AuditLog
    audit_logs = clean_db.query(AuditLog).filter(AuditLog.proposal_id == proposal_id).all()
    assert len(audit_logs) >= 2
    
    # Clean up
    clean_db.query(AuditLog).filter(AuditLog.proposal_id == proposal_id).delete()
    clean_db.query(ShieldDecision).filter(ShieldDecision.proposal_id == proposal_id).delete()
    clean_db.query(AgentProposal).filter(AgentProposal.id == proposal_id).delete()
    clean_db.commit()
