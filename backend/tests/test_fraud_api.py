import pytest
from fastapi.testclient import TestClient
from unittest.mock import MagicMock
from app.main import app
from app.api.fraud import fraud_service
from app.ml.inference.exceptions import (
    FraudModelArtifactNotFoundError,
    FraudModelLoadError,
    FraudModelPredictionError,
)
from app.ml.inference.risk_classifier import FraudRiskLevel, FraudRiskClassifier

client = TestClient(app)

# Valid sample transaction input containing all 10 required features
VALID_PAYLOAD = {
    "Amount": 150.0,
    "Merchant_Category": "Retail",
    "Distance_from_Home": 1.2,
    "Device_Type": "Mobile",
    "IP_Risk_Score": 0.05,
    "Avg_Spending_Habit": 80.0,
    "Is_Weekend": 0,
    "Is_Night_Transaction": 0,
    "Transaction_Hour": 14,
    "Day_of_Week": 2,
}

@pytest.fixture
def mock_predictor():
    """Fixture to mock the predictor dependency in fraud_service."""
    mock_pred = MagicMock()
    mock_pred.get_metadata.return_value = {
        "model_name": "HistGradientBoostingClassifier",
        "model_version": "1.0.0-test",
        "prediction": {
            "fraud_classification_threshold": 0.25,
            "risk_thresholds": {
                "medium": 0.40,
                "high": 0.70
            }
        }
    }
    # Mock risk classifier
    mock_classifier = FraudRiskClassifier(medium_threshold=0.40, high_threshold=0.70)
    mock_pred.get_risk_classifier.return_value = mock_classifier
    
    # Save original predictor
    original_predictor = fraud_service._predictor
    fraud_service._predictor = mock_pred
    
    yield mock_pred
    
    # Restore original predictor after test
    fraud_service._predictor = original_predictor


def test_predict_fraud_success(mock_predictor):
    """1. Valid prediction returns HTTP 200 and matches expected structure."""
    mock_predictor.predict.return_value = 0.85
    
    response = client.post("/api/v1/fraud/predict", json=VALID_PAYLOAD)
    assert response.status_code == 200
    
    data = response.json()
    # 2. Response contains fraud_probability
    assert "fraud_probability" in data
    # 3. fraud_probability is between 0 and 1
    assert 0.0 <= data["fraud_probability"] <= 1.0
    assert data["fraud_probability"] == 0.85
    
    # 4. Response contains risk_level
    assert "risk_level" in data
    # 5. risk_level is one of LOW, MEDIUM, HIGH
    assert data["risk_level"] == "HIGH"
    
    # 6. Response contains is_fraud
    assert "is_fraud" in data
    assert data["is_fraud"] is True
    
    # 7. Response contains model_version
    assert "model_version" in data
    assert data["model_version"] == "1.0.0-test"
    
    # Backward compatibility checks
    assert data["probability"] == 0.85
    assert data["threshold"] == 0.25
    assert data["model_name"] == "HistGradientBoostingClassifier"


def test_predict_fraud_missing_feature(mock_predictor):
    """8. Missing required input feature returns 422."""
    invalid_payload = VALID_PAYLOAD.copy()
    del invalid_payload["Amount"]
    
    response = client.post("/api/v1/fraud/predict", json=invalid_payload)
    assert response.status_code == 422
    assert "detail" in response.json()


def test_predict_fraud_invalid_type(mock_predictor):
    """9. Invalid input type returns validation error (422)."""
    invalid_payload = VALID_PAYLOAD.copy()
    invalid_payload["Merchant_Category"] = 12345  # Should be string (or converted, but Pydantic string validation checks)
    invalid_payload["Amount"] = "abc"  # Should be float
    
    response = client.post("/api/v1/fraud/predict", json=invalid_payload)
    assert response.status_code == 422


def test_predict_fraud_negative_amount_and_ranges(mock_predictor):
    """10. Negative amount or invalid numeric range is rejected."""
    # Negative amount
    payload = VALID_PAYLOAD.copy()
    payload["Amount"] = -10.0
    response = client.post("/api/v1/fraud/predict", json=payload)
    assert response.status_code == 422
    
    # IP Risk Score out of bounds
    payload = VALID_PAYLOAD.copy()
    payload["IP_Risk_Score"] = 1.5
    response = client.post("/api/v1/fraud/predict", json=payload)
    assert response.status_code == 422

    # Hour out of bounds
    payload = VALID_PAYLOAD.copy()
    payload["Transaction_Hour"] = 25
    response = client.post("/api/v1/fraud/predict", json=payload)
    assert response.status_code == 422


def test_predict_fraud_artifact_not_found(mock_predictor):
    """11. Missing model artifact maps to controlled 503 and does not expose tracebacks/paths."""
    # Mock predictor to raise FraudModelArtifactNotFoundError
    mock_predictor.predict.side_effect = FraudModelArtifactNotFoundError("Artifact path not found: /sensitive/path/to/model")
    
    response = client.post("/api/v1/fraud/predict", json=VALID_PAYLOAD)
    assert response.status_code == 503
    
    data = response.json()
    assert "detail" in data
    # 14. API error response does not expose stack traces
    assert "Traceback" not in data["detail"]
    # 15. API error response does not expose artifact filesystem paths
    assert "/sensitive/" not in data["detail"]
    assert "model artifacts not found" in data["detail"]


def test_predict_fraud_load_failure(mock_predictor):
    """12. Model loading failure maps to controlled 503."""
    mock_predictor.predict.side_effect = FraudModelLoadError("joblib read error")
    
    response = client.post("/api/v1/fraud/predict", json=VALID_PAYLOAD)
    assert response.status_code == 503
    
    data = response.json()
    assert "detail" in data
    assert "joblib" not in data["detail"]
    assert "model failed to load" in data["detail"]


def test_predict_fraud_prediction_failure(mock_predictor):
    """13. Prediction failure maps to controlled 500."""
    mock_predictor.predict.side_effect = FraudModelPredictionError("Internal sklearn error")
    
    response = client.post("/api/v1/fraud/predict", json=VALID_PAYLOAD)
    assert response.status_code == 500
    
    data = response.json()
    assert "detail" in data
    assert "sklearn" not in data["detail"]
    assert "prediction execution failed" in data["detail"]


def test_multiple_requests_reuse_singleton():
    """16. Multiple requests reuse the cached predictor."""
    # Verify that get_fraud_predictor returns the same instance on multiple calls
    from app.ml.inference.predictor import get_fraud_predictor
    p1 = get_fraud_predictor()
    p2 = get_fraud_predictor()
    assert p1 is p2
