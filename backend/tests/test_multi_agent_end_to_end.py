import uuid
import pytest
from decimal import Decimal
from unittest.mock import patch, MagicMock, ANY
from fastapi.testclient import TestClient

from app.main import app
from app.database.session import SessionLocal
from app.database.models.transaction import Transaction
from app.database.models.customer import Customer
from app.database.models.merchant import Merchant
from app.database.models.agent import Agent
from app.database.models.event_workflow import EventWorkflow
from app.database.models.agent_proposal import AgentProposal
from app.database.models.shield_decision import ShieldDecision
from app.database.models.audit_log import AuditLog
from app.database.models.enums import AgentType, ProposalStatus, ShieldDecisionType, TransactionStatus, ImpactLevel
from app.ml.inference.service import FraudPredictionResult
from app.ml.inference.risk_classifier import FraudRiskLevel

client = TestClient(app)

class MockRetrievedPolicy:
    def __init__(self, key, desc, name="Mock Policy"):
        self.policy_key = key
        self.rule_description = desc
        self.description = desc
        self.document_content = desc
        self.policy_name = name
        self.similarity_score = 0.92

@pytest.fixture
def clean_db():
    db = SessionLocal()
    yield db
    db.close()

def clean_event_data(db, event_id):
    db.query(AuditLog).filter(AuditLog.proposal_id.in_(
        db.query(AgentProposal.id).filter(AgentProposal.event_id == str(event_id))
    )).delete(synchronize_session=False)
    db.query(ShieldDecision).filter(ShieldDecision.proposal_id.in_(
        db.query(AgentProposal.id).filter(AgentProposal.event_id == str(event_id))
    )).delete(synchronize_session=False)
    db.query(AgentProposal).filter(AgentProposal.event_id == str(event_id)).delete(synchronize_session=False)
    db.query(EventWorkflow).filter(EventWorkflow.event_id == str(event_id)).delete(synchronize_session=False)
    db.commit()


@patch("app.llm.provider.LLMProvider.generate_structured_output")
@patch("app.ml.inference.service.FraudPredictionService.predict_transaction")
def test_scenario_1_fraud_only(mock_predict, mock_gen, clean_db):
    """
    Scenario 1: Fraud-Only Workflow
    Triggered by a PENDING transaction event. Only Fraud Agent executes.
    """
    mock_predict.return_value = FraudPredictionResult(
        fraud_probability=0.05,
        probability=0.05,
        risk_level=FraudRiskLevel.LOW,
        is_fraud=False,
        threshold=0.25,
        model_version="1.0.0",
        model_name="HistGradientBoostingClassifier"
    )
    
    mock_gen.return_value = {
        "proposed_action": "ALLOW_TRANSACTION",
        "action_parameters": None,
        "confidence": 0.95,
        "evidence": [],
        "reason_summary": "Transaction risk is very low.",
        "financial_impact": "LOW",
        "customer_impact": "LOW"
    }

    # Fetch tx_vc_103
    tx = clean_db.query(Transaction).filter(Transaction.external_transaction_id == "tx_vc_103").first()
    assert tx is not None
    
    original_status = tx.status
    tx.status = TransactionStatus.PENDING
    clean_db.commit()

    clean_event_data(clean_db, tx.id)

    try:
        payload = {
            "event_type": "TRANSACTION",
            "event_id": str(tx.id)
        }
        
        response = client.post("/api/v1/agentshield/process-event", json=payload)
        assert response.status_code == 201
        data = response.json()
        
        # Only Fraud agent should have executed
        assert data["status"] == "COMPLETED"
        assert "FRAUD" in data["executed_agents"]
        assert "RECOVERY" not in data["executed_agents"]
        assert "GROWTH" not in data["executed_agents"]
        assert data["final_decision"] == "APPROVE"
        
        # Cleanup
        clean_event_data(clean_db, tx.id)

    finally:
        tx.status = original_status
        clean_db.commit()


@patch("app.llm.provider.LLMProvider.generate_structured_output")
@patch("app.rag.retrieval.retrieve_relevant_policies_sync")
def test_scenario_2_recovery(mock_retrieve, mock_gen, clean_db):
    """
    Scenario 2: Recovery Workflow with RAG
    Verifies that a PAYMENT_FAILURE event retrieves merchant policies scoping correctly,
    runs RecoveryAgent, and decides via AgentShield.
    """
    mock_retrieve.return_value = [
        MockRetrievedPolicy("max_recovery_retries", "Permit up to 3 payment retries.", "Max Recovery Retries")
    ]
    
    mock_gen.return_value = {
        "proposed_action": "WAIT_AND_RETRY",
        "action_parameters": {"retry_delay_seconds": 60},
        "confidence": 0.90,
        "evidence": ["NETWORK_ERROR"],
        "reason_summary": "Simulating network retry.",
        "financial_impact": "LOW",
        "customer_impact": "LOW"
    }

    tx = clean_db.query(Transaction).filter(Transaction.status == TransactionStatus.FAILED).first()
    assert tx is not None

    clean_event_data(clean_db, tx.id)

    payload = {
        "event_type": "PAYMENT_FAILURE",
        "event_id": str(tx.id)
    }

    with patch("app.ml.inference.service.FraudPredictionService.predict_transaction", side_effect=Exception("Degraded")):
        response = client.post("/api/v1/agentshield/process-event", json=payload)
    
    assert response.status_code == 201
    data = response.json()
    assert "RECOVERY" in data["executed_agents"]
    
    # Assert RAG is scoped correctly
    mock_retrieve.assert_called_once()
    assert mock_retrieve.call_args[0][1] == tx.merchant_id

    # Cleanup
    clean_event_data(clean_db, tx.id)


@patch("app.llm.provider.LLMProvider.generate_structured_output")
@patch("app.rag.retrieval.retrieve_relevant_policies_sync")
def test_scenario_3_growth(mock_retrieve, mock_gen, clean_db):
    """
    Scenario 3: Growth Workflow with RAG
    Triggered by a GROWTH_OPPORTUNITY event.
    """
    mock_retrieve.return_value = [
        MockRetrievedPolicy("max_discount_percent", "Limit maximum incentive discount to 10%.", "Max Discount Percent")
    ]
    
    mock_gen.return_value = {
        "proposed_action": "APPLY_DISCOUNT",
        "action_parameters": {"discount_percent": 5},
        "confidence": 0.85,
        "evidence": ["LOYAL_CUSTOMER"],
        "reason_summary": "Loyalty promotion proposal.",
        "financial_impact": "LOW",
        "customer_impact": "LOW"
    }

    customer = clean_db.query(Customer).first()
    assert customer is not None

    clean_event_data(clean_db, customer.id)

    payload = {
        "event_type": "GROWTH_OPPORTUNITY",
        "event_id": str(customer.id)
    }

    response = client.post("/api/v1/agentshield/process-event", json=payload)
    assert response.status_code == 201
    data = response.json()
    assert "GROWTH" in data["executed_agents"]
    
    # RAG scoped to customer merchant
    mock_retrieve.assert_called_once()
    assert mock_retrieve.call_args[0][1] == customer.merchant_id
    assert data["final_decision"] == "APPROVE"

    # Cleanup
    clean_event_data(clean_db, customer.id)


@patch("app.llm.provider.LLMProvider.generate_structured_output")
@patch("app.rag.retrieval.retrieve_relevant_policies_sync")
@patch("app.ml.inference.service.FraudPredictionService.predict_transaction")
def test_scenario_4_multi_agent(mock_predict, mock_retrieve, mock_gen, clean_db):
    """
    Scenario 4: Multi-Agent Workflow
    Verifies that a TRANSACTION event on a FAILED transaction executes both Fraud and Recovery agents.
    """
    mock_predict.return_value = FraudPredictionResult(
        fraud_probability=0.08,
        probability=0.08,
        risk_level=FraudRiskLevel.LOW,
        is_fraud=False,
        threshold=0.25,
        model_version="1.0.0",
        model_name="HistGradientBoostingClassifier"
    )
    
    mock_retrieve.return_value = [
        MockRetrievedPolicy("max_recovery_retries", "Up to 3 retries.", "Max Recovery Retries")
    ]
    
    mock_gen.side_effect = [
        # Call 1 (Fraud Agent)
        {
            "proposed_action": "ALLOW_TRANSACTION",
            "action_parameters": None,
            "confidence": 0.95,
            "evidence": [],
            "reason_summary": "Risk check completed successfully.",
            "financial_impact": "LOW",
            "customer_impact": "LOW"
        },
        # Call 2 (Recovery Agent)
        {
            "proposed_action": "WAIT_AND_RETRY",
            "action_parameters": {"retry_delay_seconds": 30},
            "confidence": 0.88,
            "evidence": ["TEMPORARY_CONNECTION_ISSUE"],
            "reason_summary": "Retrying connection failure.",
            "financial_impact": "LOW",
            "customer_impact": "LOW"
        }
    ]

    tx = clean_db.query(Transaction).filter(Transaction.status == TransactionStatus.FAILED).first()
    assert tx is not None

    clean_event_data(clean_db, tx.id)

    payload = {
        "event_type": "TRANSACTION",
        "event_id": str(tx.id)
    }

    response = client.post("/api/v1/agentshield/process-event", json=payload)
    assert response.status_code == 201
    data = response.json()
    
    assert "FRAUD" in data["executed_agents"]
    assert "RECOVERY" in data["executed_agents"]
    assert len(data["proposals"]) == 2
    assert len(data["decision_details"]) == 2

    # Cleanup
    clean_event_data(clean_db, tx.id)


@patch("app.services.orchestration_service.orchestrate_agent")
def test_scenario_5_conflicting_proposals(mock_orchestrate, clean_db):
    """
    Scenario 5: Conflicting Proposals
    Fraud proposes BLOCK_TRANSACTION (resolves to REJECT/ESCALATE) and Recovery proposes WAIT_AND_RETRY.
    """
    f_agent = clean_db.query(Agent).filter(Agent.agent_type == AgentType.FRAUD).first()
    r_agent = clean_db.query(Agent).filter(Agent.agent_type == AgentType.RECOVERY).first()
    merchant = clean_db.query(Merchant).first()
    tx = clean_db.query(Transaction).filter(Transaction.status == TransactionStatus.FAILED).first()

    clean_event_data(clean_db, tx.id)

    # Fraud proposal (fresh ID, references real tx ID to allow loading context)
    p1 = AgentProposal(
        id=uuid.uuid4(),
        agent_id=f_agent.id,
        merchant_id=merchant.id,
        event_type="TRANSACTION",
        event_id=str(tx.id),
        action="BLOCK_TRANSACTION",
        action_parameters=None,
        confidence=Decimal("0.95"),
        financial_impact=ImpactLevel.MEDIUM,
        customer_impact=ImpactLevel.HIGH,
        evidence=["SUSPICIOUS_ML_SCORE"],
        reason_summary="Fraud block",
        status=ProposalStatus.PENDING
    )
    clean_db.add(p1)

    # Recovery proposal (fresh ID, references real tx ID to allow loading context)
    p2 = AgentProposal(
        id=uuid.uuid4(),
        agent_id=r_agent.id,
        merchant_id=merchant.id,
        event_type="PAYMENT_FAILURE",
        event_id=str(tx.id),
        action="WAIT_AND_RETRY",
        action_parameters={"retry_delay_seconds": 30},
        confidence=Decimal("0.85"),
        financial_impact=ImpactLevel.LOW,
        customer_impact=ImpactLevel.LOW,
        evidence=["FAILED_CARD"],
        reason_summary="Recovery retry",
        status=ProposalStatus.PENDING
    )
    clean_db.add(p2)
    clean_db.commit()
    clean_db.refresh(p1)
    clean_db.refresh(p2)

    mock_orchestrate.side_effect = [p1, p2]

    payload = {
        "event_type": "TRANSACTION",
        "event_id": str(tx.id)
    }

    response = client.post("/api/v1/agentshield/process-event", json=payload)
    assert response.status_code == 201
    data = response.json()
    
    assert data["final_decision"] in ("REJECT", "ESCALATE")

    # Cleanup
    clean_event_data(clean_db, tx.id)


@patch("app.services.orchestration_service.orchestrate_agent")
def test_scenario_6_single_agent_failure(mock_orchestrate, clean_db):
    """
    Scenario 6: Single-Agent Failure
    Fraud agent fails, but Recovery agent executes successfully.
    """
    r_agent = clean_db.query(Agent).filter(Agent.agent_type == AgentType.RECOVERY).first()
    merchant = clean_db.query(Merchant).first()
    tx = clean_db.query(Transaction).filter(Transaction.status == TransactionStatus.FAILED).first()

    clean_event_data(clean_db, tx.id)

    p2 = AgentProposal(
        id=uuid.uuid4(),
        agent_id=r_agent.id,
        merchant_id=merchant.id,
        event_type="PAYMENT_FAILURE",
        event_id=str(tx.id),
        action="WAIT_AND_RETRY",
        action_parameters={"retry_delay_seconds": 30},
        confidence=Decimal("0.85"),
        financial_impact=ImpactLevel.LOW,
        customer_impact=ImpactLevel.LOW,
        evidence=["FAILED_CARD"],
        reason_summary="Recovery retry",
        status=ProposalStatus.PENDING
    )
    clean_db.add(p2)
    clean_db.commit()
    clean_db.refresh(p2)

    mock_orchestrate.side_effect = [Exception("Gemini context timeout"), p2]

    payload = {
        "event_type": "TRANSACTION",
        "event_id": str(tx.id)
    }

    response = client.post("/api/v1/agentshield/process-event", json=payload)
    assert response.status_code == 201
    data = response.json()

    assert data["status"] == "DEGRADED"
    assert data["final_decision"] == "APPROVE"

    # Cleanup
    clean_event_data(clean_db, tx.id)


@patch("app.llm.provider.LLMProvider.generate_structured_output")
@patch("app.rag.retrieval.retrieve_relevant_policies_sync")
def test_scenario_7_tenant_isolation(mock_retrieve, mock_gen, clean_db):
    """
    Scenario 7: Tenant Isolation
    Verifies no policy leaks occur across merchant boundaries.
    """
    mock_retrieve.return_value = []
    mock_gen.return_value = {
        "proposed_action": "APPLY_DISCOUNT",
        "action_parameters": {"discount_percent": 10},
        "confidence": 0.85,
        "evidence": [],
        "reason_summary": "Clean loyalty proposal.",
        "financial_impact": "LOW",
        "customer_impact": "LOW"
    }

    c1 = clean_db.query(Customer).first()
    c2 = clean_db.query(Customer).filter(Customer.merchant_id != c1.merchant_id).first()
    assert c1 is not None
    assert c2 is not None

    clean_event_data(clean_db, c1.id)
    clean_event_data(clean_db, c2.id)

    # Step 1: Evaluate c1
    response = client.post("/api/v1/agentshield/process-event", json={"event_type": "GROWTH_OPPORTUNITY", "event_id": str(c1.id)})
    assert response.status_code == 201
    mock_retrieve.assert_called_with(ANY, c1.merchant_id, ANY, limit=ANY)

    # Step 2: Evaluate c2
    response = client.post("/api/v1/agentshield/process-event", json={"event_type": "GROWTH_OPPORTUNITY", "event_id": str(c2.id)})
    assert response.status_code == 201
    mock_retrieve.assert_called_with(ANY, c2.merchant_id, ANY, limit=ANY)

    # Cleanup
    clean_event_data(clean_db, c1.id)
    clean_event_data(clean_db, c2.id)
