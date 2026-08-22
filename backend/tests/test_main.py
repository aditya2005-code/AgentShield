from fastapi.testclient import TestClient
from app.main import app

client = TestClient(app)

def test_health_check():
    response = client.get("/health")
    assert response.status_code == 200
    data = response.json()
    assert "status" in data
    assert "database" in data
    assert data["day"] == 2

def test_get_agents():
    response = client.get("/api/v1/agents")
    assert response.status_code == 200
    data = response.json()
    assert isinstance(data, list)
    assert len(data) >= 3
    # Check that core keys exist
    keys = {a["agent_key"] for a in data}
    assert "fraud_agent" in keys
    assert "recovery_agent" in keys
    assert "growth_agent" in keys

def test_get_transactions():
    response = client.get("/api/v1/transactions?limit=5")
    assert response.status_code == 200
    data = response.json()
    assert isinstance(data, list)
    assert len(data) <= 5

def test_get_demo_scenarios_list():
    response = client.get("/api/v1/demo/scenarios")
    assert response.status_code == 200
    data = response.json()
    assert "scenarios" in data
    assert "fraud" in data["scenarios"]
    assert "recovery" in data["scenarios"]
    assert "growth" in data["scenarios"]

def test_get_demo_scenario_fraud():
    response = client.get("/api/v1/demo/scenarios/fraud")
    assert response.status_code == 200
    data = response.json()
    assert "event" in data
    assert "agent" in data
    assert "proposal" in data
    assert "shield_decision" in data
    assert "audit_logs" in data
    assert data["agent"]["agent_key"] == "fraud_agent"
    assert data["shield_decision"]["decision"] == "APPROVE"

def test_get_demo_scenario_growth():
    response = client.get("/api/v1/demo/scenarios/growth")
    assert response.status_code == 200
    data = response.json()
    assert "event" in data
    assert "agent" in data
    assert "proposal" in data
    assert "shield_decision" in data
    assert "audit_logs" in data
    assert data["agent"]["agent_key"] == "growth_agent"
    assert data["shield_decision"]["decision"] == "MODIFY"
    assert data["shield_decision"]["modified_from"]["discount_percent"] == 25
    assert data["shield_decision"]["final_action_parameters"]["discount_percent"] == 10
