import uuid
import pytest
from decimal import Decimal
from unittest.mock import patch, MagicMock, ANY
from sqlalchemy.exc import IntegrityError
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
        self.similarity_score = 0.95

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


# ==========================================
# OBJECTIVE 1 — Verify & Correct Agent Routing Tests
# ==========================================

@patch("app.llm.provider.LLMProvider.generate_structured_output")
@patch("app.rag.retrieval.retrieve_relevant_policies_sync")
@patch("app.ml.inference.service.FraudPredictionService.predict_transaction")
def test_routing_scenarios(mock_predict, mock_retrieve, mock_gen, clean_db):
    mock_predict.return_value = FraudPredictionResult(
        fraud_probability=0.01, risk_level=FraudRiskLevel.LOW, is_fraud=False,
        probability=0.01, threshold=0.25, model_version="1.0.0", model_name="Mock"
    )
    mock_retrieve.return_value = [MockRetrievedPolicy("max_discount_percent", "Limit: 10%")]
    mock_gen.return_value = {
        "proposed_action": "ALLOW_TRANSACTION", "action_parameters": None, "confidence": 0.95,
        "evidence": [], "reason_summary": "Low risk.", "financial_impact": "LOW", "customer_impact": "LOW"
    }

    # 1. SUCCESS transaction -> Fraud + Growth
    tx_success = clean_db.query(Transaction).filter(Transaction.status == TransactionStatus.SUCCESS).first()
    clean_event_data(clean_db, tx_success.id)
    response = client.post("/api/v1/agentshield/process-event", json={"event_type": "TRANSACTION", "event_id": str(tx_success.id)})
    assert response.status_code == 201
    data = response.json()
    assert "FRAUD" in data["executed_agents"]
    assert "GROWTH" in data["executed_agents"]
    assert "RECOVERY" not in data["executed_agents"]
    clean_event_data(clean_db, tx_success.id)

    # 2. FAILED transaction -> Fraud + Recovery
    tx_failed = clean_db.query(Transaction).filter(Transaction.status == TransactionStatus.FAILED).first()
    clean_event_data(clean_db, tx_failed.id)
    response = client.post("/api/v1/agentshield/process-event", json={"event_type": "TRANSACTION", "event_id": str(tx_failed.id)})
    assert response.status_code == 201
    data = response.json()
    assert "FRAUD" in data["executed_agents"]
    assert "RECOVERY" in data["executed_agents"]
    assert "GROWTH" not in data["executed_agents"]
    clean_event_data(clean_db, tx_failed.id)

    # 3. BLOCKED transaction -> Fraud + Recovery
    tx_blocked = clean_db.query(Transaction).filter(Transaction.status == TransactionStatus.BLOCKED).first()
    clean_event_data(clean_db, tx_blocked.id)
    response = client.post("/api/v1/agentshield/process-event", json={"event_type": "TRANSACTION", "event_id": str(tx_blocked.id)})
    assert response.status_code == 201
    data = response.json()
    assert "FRAUD" in data["executed_agents"]
    assert "RECOVERY" in data["executed_agents"]
    assert "GROWTH" not in data["executed_agents"]
    clean_event_data(clean_db, tx_blocked.id)

    # 4. PAYMENT_FAILURE -> Recovery + Fraud (if sufficient context)
    clean_event_data(clean_db, tx_failed.id)
    response = client.post("/api/v1/agentshield/process-event", json={"event_type": "PAYMENT_FAILURE", "event_id": str(tx_failed.id)})
    assert response.status_code == 201
    data = response.json()
    assert "RECOVERY" in data["executed_agents"]
    assert "FRAUD" in data["executed_agents"]
    assert "GROWTH" not in data["executed_agents"]
    clean_event_data(clean_db, tx_failed.id)

    # 5. GROWTH_OPPORTUNITY -> Growth
    cust = clean_db.query(Customer).first()
    clean_event_data(clean_db, cust.id)
    response = client.post("/api/v1/agentshield/process-event", json={"event_type": "GROWTH_OPPORTUNITY", "event_id": str(cust.id)})
    assert response.status_code == 201
    data = response.json()
    assert "GROWTH" in data["executed_agents"]
    assert "FRAUD" not in data["executed_agents"]
    assert "RECOVERY" not in data["executed_agents"]
    clean_event_data(clean_db, cust.id)

    # 6. Regression test for tx_vc_402 (PAYMENT_FAILURE event on successful transaction)
    tx_vc_402 = clean_db.query(Transaction).filter(Transaction.external_transaction_id == "tx_vc_402").first()
    clean_event_data(clean_db, tx_vc_402.id)
    response = client.post("/api/v1/agentshield/process-event", json={"event_type": "PAYMENT_FAILURE", "event_id": str(tx_vc_402.id)})
    assert response.status_code == 201
    data = response.json()
    # It must execute Fraud and Recovery, but since Recovery fails on a successful status,
    # the execution runs in DEGRADED mode, but SUCCESS triggers do not pull in Growth Agent!
    assert "FRAUD" in data["executed_agents"]
    assert "GROWTH" not in data["executed_agents"]
    assert data["status"] == "DEGRADED"
    clean_event_data(clean_db, tx_vc_402.id)


# ==========================================
# OBJECTIVE 2 & 4 — Database-Backed Idempotency Tests
# ==========================================

@patch("app.llm.provider.LLMProvider.generate_structured_output")
@patch("app.rag.retrieval.retrieve_relevant_policies_sync")
@patch("app.ml.inference.service.FraudPredictionService.predict_transaction")
def test_database_idempotency_and_no_duplicates(mock_predict, mock_retrieve, mock_gen, clean_db):
    mock_predict.return_value = FraudPredictionResult(
        fraud_probability=0.01, risk_level=FraudRiskLevel.LOW, is_fraud=False,
        probability=0.01, threshold=0.25, model_version="1.0.0", model_name="Mock"
    )
    mock_retrieve.return_value = [MockRetrievedPolicy("max_discount_percent", "Limit: 10%")]
    mock_gen.return_value = {
        "proposed_action": "ALLOW_TRANSACTION", "action_parameters": None, "confidence": 0.95,
        "evidence": [], "reason_summary": "Low risk.", "financial_impact": "LOW", "customer_impact": "LOW"
    }

    cust = clean_db.query(Customer).first()
    clean_event_data(clean_db, cust.id)

    # 7. Completed event processed twice -> agents execute only once.
    # We call it the first time.
    response1 = client.post("/api/v1/agentshield/process-event", json={"event_type": "GROWTH_OPPORTUNITY", "event_id": str(cust.id)})
    assert response1.status_code == 201
    data1 = response1.json()

    # Reset mock call history.
    mock_gen.reset_mock()

    # Call it the second time.
    response2 = client.post("/api/v1/agentshield/process-event", json={"event_type": "GROWTH_OPPORTUNITY", "event_id": str(cust.id)})
    assert response2.status_code == 201
    data2 = response2.json()

    # 8. Repeated request returns same persisted result.
    assert data1 == data2
    # Verify no agent execution occurred on second run.
    mock_gen.assert_not_called()

    # 9. No duplicate AgentProposal records.
    proposals = clean_db.query(AgentProposal).filter_by(event_id=str(cust.id)).all()
    assert len(proposals) == 1

    # 10. No duplicate ShieldDecision records.
    decisions = clean_db.query(ShieldDecision).filter(ShieldDecision.proposal_id == proposals[0].id).all()
    assert len(decisions) == 1

    # 11. No duplicate AuditLog records.
    logs = clean_db.query(AuditLog).filter(AuditLog.proposal_id == proposals[0].id).all()
    # 1 log for AGENT_PROPOSAL_CREATED, 1 for SHIELD_DECISION_CREATED
    assert len(logs) == 2

    clean_event_data(clean_db, cust.id)


# ==========================================
# OBJECTIVE 3 — Event Processing Lifecycle Tests
# ==========================================

@patch("app.llm.provider.LLMProvider.generate_structured_output")
@patch("app.rag.retrieval.retrieve_relevant_policies_sync")
@patch("app.ml.inference.service.FraudPredictionService.predict_transaction")
def test_event_lifecycle_and_retry(mock_predict, mock_retrieve, mock_gen, clean_db):
    mock_predict.return_value = FraudPredictionResult(
        fraud_probability=0.01, risk_level=FraudRiskLevel.LOW, is_fraud=False,
        probability=0.01, threshold=0.25, model_version="1.0.0", model_name="Mock"
    )
    mock_retrieve.return_value = [MockRetrievedPolicy("max_discount_percent", "Limit: 10%")]
    mock_gen.return_value = {
        "proposed_action": "ALLOW_TRANSACTION", "action_parameters": None, "confidence": 0.95,
        "evidence": [], "reason_summary": "Low risk.", "financial_impact": "LOW", "customer_impact": "LOW"
    }

    cust = clean_db.query(Customer).first()
    clean_event_data(clean_db, cust.id)

    # 12. PENDING -> PROCESSING -> COMPLETED lifecycle transitions.
    response = client.post("/api/v1/agentshield/process-event", json={"event_type": "GROWTH_OPPORTUNITY", "event_id": str(cust.id)})
    assert response.status_code == 201
    
    clean_db.rollback()
    workflow = clean_db.query(EventWorkflow).filter_by(event_type="GROWTH_OPPORTUNITY", event_id=str(cust.id)).first()
    assert workflow is not None
    assert workflow.status == "COMPLETED"
    clean_event_data(clean_db, cust.id)

    # 13. DEGRADED execution remains distinct from FAILED.
    # Trigger PAYMENT_FAILURE on success tx_vc_402. Recovery fails, Fraud succeeds.
    tx_vc_402 = clean_db.query(Transaction).filter(Transaction.external_transaction_id == "tx_vc_402").first()
    clean_event_data(clean_db, tx_vc_402.id)
    response = client.post("/api/v1/agentshield/process-event", json={"event_type": "PAYMENT_FAILURE", "event_id": str(tx_vc_402.id)})
    data = response.json()
    assert data["status"] == "DEGRADED"
    
    clean_db.rollback()
    workflow = clean_db.query(EventWorkflow).filter_by(event_type="PAYMENT_FAILURE", event_id=str(tx_vc_402.id)).first()
    assert workflow.status == "COMPLETED"  # Workflow is completed because we successfully got a final decision!
    clean_event_data(clean_db, tx_vc_402.id)

    # 14. Controlled processing failure produces correct FAILED state.
    # Force orchestrate_agent to throw an Exception for a single Growth Opportunity.
    with patch("app.services.orchestration_service.orchestrate_agent", side_effect=Exception("Failed")):
        response = client.post("/api/v1/agentshield/process-event", json={"event_type": "GROWTH_OPPORTUNITY", "event_id": str(cust.id)})
    data = response.json()
    assert data["status"] == "FAILED"
    
    clean_db.rollback()
    workflow = clean_db.query(EventWorkflow).filter_by(event_type="GROWTH_OPPORTUNITY", event_id=str(cust.id)).first()
    assert workflow.status == "FAILED"

    # 15. Safe retry after controlled failure.
    # Running it again under mock success triggers the retry logic, executing and completing correctly.
    response_retry = client.post("/api/v1/agentshield/process-event", json={"event_type": "GROWTH_OPPORTUNITY", "event_id": str(cust.id)})
    assert response_retry.status_code == 201
    data_retry = response_retry.json()
    assert data_retry["status"] == "COMPLETED"
    
    clean_db.rollback()
    workflow = clean_db.query(EventWorkflow).filter_by(event_type="GROWTH_OPPORTUNITY", event_id=str(cust.id)).first()
    assert workflow.status == "COMPLETED"
    clean_event_data(clean_db, cust.id)

    # 16. Simulated concurrent/duplicate processing cannot execute event twice.
    # Seed a PROCESSING row in the database. A concurrent call must immediately get in-progress response.
    workflow_proc = EventWorkflow(
        event_type="GROWTH_OPPORTUNITY",
        event_id=str(cust.id),
        merchant_id=cust.merchant_id,
        status="PROCESSING"
    )
    clean_db.add(workflow_proc)
    clean_db.commit()

    response_concurrent = client.post("/api/v1/agentshield/process-event", json={"event_type": "GROWTH_OPPORTUNITY", "event_id": str(cust.id)})
    assert response_concurrent.status_code == 201
    data_concurrent = response_concurrent.json()
    assert data_concurrent["status"] == "PROCESSING"

    clean_event_data(clean_db, cust.id)


# ==========================================
# OBJECTIVE 5 — Conflict Resolution Tests
# ==========================================

@patch("app.services.orchestration_service.orchestrate_agent")
def test_conflict_resolution_hierarchy(mock_orchestrate, clean_db):
    f_agent = clean_db.query(Agent).filter(Agent.agent_type == AgentType.FRAUD).first()
    r_agent = clean_db.query(Agent).filter(Agent.agent_type == AgentType.RECOVERY).first()
    merchant = clean_db.query(Merchant).first()
    tx = clean_db.query(Transaction).filter(Transaction.status == TransactionStatus.FAILED).first()

    clean_event_data(clean_db, tx.id)

    # Mock proposals for Fraud and Recovery agents
    p1 = AgentProposal(
        id=uuid.uuid4(), agent_id=f_agent.id, merchant_id=merchant.id,
        event_type="TRANSACTION", event_id=str(tx.id), action="BLOCK_TRANSACTION",
        action_parameters=None, confidence=Decimal("0.90"), financial_impact=ImpactLevel.MEDIUM,
        customer_impact=ImpactLevel.HIGH, evidence=[], reason_summary="Mock", status=ProposalStatus.PENDING
    )
    p2 = AgentProposal(
        id=uuid.uuid4(), agent_id=r_agent.id, merchant_id=merchant.id,
        event_type="PAYMENT_FAILURE", event_id=str(tx.id), action="WAIT_AND_RETRY",
        action_parameters={"retry_delay_seconds": 30}, confidence=Decimal("0.85"), financial_impact=ImpactLevel.LOW,
        customer_impact=ImpactLevel.LOW, evidence=[], reason_summary="Mock", status=ProposalStatus.PENDING
    )
    clean_db.add_all([p1, p2])
    clean_db.commit()

    mock_orchestrate.side_effect = [p1, p2]

    # 17. Conflicting outcomes resolve correctly.
    # 18. Most protective outcome wins. (BLOCK_TRANSACTION triggers WARNING on customer impact, resolving to ESCALATE)
    response = client.post("/api/v1/agentshield/process-event", json={"event_type": "TRANSACTION", "event_id": str(tx.id)})
    data = response.json()
    assert data["final_decision"] in ("ESCALATE", "REJECT")

    clean_event_data(clean_db, tx.id)


# ==========================================
# OBJECTIVE 6 — Production API Verification Tests
# ==========================================

@patch("app.llm.provider.LLMProvider.generate_structured_output")
@patch("app.rag.retrieval.retrieve_relevant_policies_sync")
@patch("app.ml.inference.service.FraudPredictionService.predict_transaction")
def test_api_hardening_and_validation(mock_predict, mock_retrieve, mock_gen, clean_db):
    mock_predict.return_value = FraudPredictionResult(
        fraud_probability=0.01, risk_level=FraudRiskLevel.LOW, is_fraud=False,
        probability=0.01, threshold=0.25, model_version="1.0.0", model_name="Mock"
    )
    mock_retrieve.return_value = [MockRetrievedPolicy("max_discount_percent", "Limit: 10%")]
    mock_gen.return_value = {
        "proposed_action": "ALLOW_TRANSACTION", "action_parameters": None, "confidence": 0.95,
        "evidence": [], "reason_summary": "Low risk.", "financial_impact": "LOW", "customer_impact": "LOW"
    }

    cust = clean_db.query(Customer).first()
    clean_event_data(clean_db, cust.id)

    # 19. Successful orchestration request
    response = client.post("/api/v1/agentshield/process-event", json={"event_type": "GROWTH_OPPORTUNITY", "event_id": str(cust.id)})
    assert response.status_code == 201
    
    # 20. Repeated idempotent API request
    response_dup = client.post("/api/v1/agentshield/process-event", json={"event_type": "GROWTH_OPPORTUNITY", "event_id": str(cust.id)})
    assert response_dup.status_code == 201
    assert response_dup.json() == response.json()
    clean_event_data(clean_db, cust.id)

    # 21. Processing/in-progress request handling
    workflow_proc = EventWorkflow(
        event_type="GROWTH_OPPORTUNITY", event_id=str(cust.id), merchant_id=cust.merchant_id, status="PROCESSING"
    )
    clean_db.add(workflow_proc)
    clean_db.commit()
    response_proc = client.post("/api/v1/agentshield/process-event", json={"event_type": "GROWTH_OPPORTUNITY", "event_id": str(cust.id)})
    assert response_proc.status_code == 201
    assert response_proc.json()["status"] == "PROCESSING"
    clean_event_data(clean_db, cust.id)

    # 22. Invalid request validation (returns 422 for invalid format/event types)
    response_invalid1 = client.post("/api/v1/agentshield/process-event", json={"event_type": "INVALID", "event_id": str(cust.id)})
    assert response_invalid1.status_code == 422

    response_invalid2 = client.post("/api/v1/agentshield/process-event", json={"event_type": "GROWTH_OPPORTUNITY", "event_id": "not-a-uuid"})
    assert response_invalid2.status_code == 422

    # 23. Controlled internal error response (500 without stack trace)
    # We force process_event_orchestration to throw a raw exception. The response must hide implementation details.
    with patch("app.api.agentshield.process_event_orchestration", side_effect=Exception("/local/file/path/secret_token_123")):
        response_err = client.post("/api/v1/agentshield/process-event", json={"event_type": "GROWTH_OPPORTUNITY", "event_id": str(cust.id)})
    assert response_err.status_code == 500
    assert "secret_token_123" not in response_err.text
    assert "/local/file/path" not in response_err.text
    assert response_err.json()["detail"] == "An internal error occurred while processing the event."
