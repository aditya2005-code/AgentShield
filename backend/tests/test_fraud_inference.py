import json
import uuid
from unittest.mock import MagicMock, mock_open, patch

import numpy as np
import pandas as pd
import pytest

from app.core.config import settings
from app.ml.inference.exceptions import (
    FraudModelArtifactNotFoundError,
    FraudModelLoadError,
    FraudModelPredictionError,
)
from app.ml.inference.predictor import FraudPredictor, get_fraud_predictor
from app.ml.inference.service import FraudPredictionService

# Valid sample transaction input containing all 10 required features
MOCK_INPUT = {
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

MOCK_METADATA = {
    "model_name": "HistGradientBoostingClassifier",
    "model_version": "1.0.0-test",
    "model_iterations": 64,
    "prediction": {
        "positive_class": "fraud",
        "probability_method": "predict_proba",
        "probability_index": 1,
        "fraud_classification_threshold": 0.35,
    },
}


@pytest.fixture
def mock_predictor_dependencies():
    """Sets up mocks for file existence, joblib loading, and json reading."""
    mock_model = MagicMock()
    mock_model.predict_proba.return_value = np.array([[0.8, 0.2]])
    mock_model.classes_ = np.array([0, 1])

    mock_preprocessor = MagicMock()
    mock_preprocessor.transform.return_value = np.array([[1.0] * 10])

    with patch("pathlib.Path.exists") as mock_exists, \
         patch("builtins.open", mock_open(read_data=json.dumps(MOCK_METADATA))), \
         patch("joblib.load") as mock_joblib_load:
        
        # All files exist
        mock_exists.return_value = True
        
        # joblib loads mock model first, then preprocessor
        mock_joblib_load.side_effect = [mock_model, mock_preprocessor]
        
        yield mock_model, mock_preprocessor


def test_predictor_successful_load(mock_predictor_dependencies):
    """Test that valid artifacts are loaded and stored in cache successfully."""
    mock_model, mock_preprocessor = mock_predictor_dependencies
    
    predictor = FraudPredictor()
    predictor.load()
    
    assert predictor.is_loaded() is True
    assert predictor.get_metadata()["model_version"] == "1.0.0-test"
    assert predictor.get_model_info()["fraud_classification_threshold"] == 0.35
    assert predictor._model == mock_model
    assert predictor._preprocessor == mock_preprocessor


def test_predictor_caching_behavior(mock_predictor_dependencies):
    """Test that artifacts are cached in-memory and not reloaded from disk on subsequent calls."""
    mock_model, mock_preprocessor = mock_predictor_dependencies
    
    with patch("joblib.load") as spy_joblib_load:
        spy_joblib_load.side_effect = [mock_model, mock_preprocessor]
        
        predictor = FraudPredictor()
        predictor.load()
        assert predictor.is_loaded() is True
        
        # Call load again
        predictor.load()
        
        # joblib.load should only be called twice (during the first load call)
        assert spy_joblib_load.call_count == 2


def test_predictor_missing_model_file():
    """Test that missing model artifact file raises FraudModelArtifactNotFoundError."""
    with patch("pathlib.Path.exists") as mock_exists:
        # Simulate files missing
        mock_exists.return_value = False
        
        predictor = FraudPredictor()
        with pytest.raises(FraudModelArtifactNotFoundError, match="Missing ML artifact files"):
            predictor.load()


def test_predictor_missing_preprocessor_file():
    """Test that missing preprocessor artifact file raises FraudModelArtifactNotFoundError."""
    with patch("pathlib.Path.exists") as mock_exists:
        # Simulate files missing
        mock_exists.return_value = False
        
        predictor = FraudPredictor()
        with pytest.raises(FraudModelArtifactNotFoundError, match="Missing ML artifact files"):
            predictor.load()


def test_predictor_invalid_metadata_json():
    """Test that corrupted or invalid metadata JSON raises FraudModelLoadError."""
    with patch("pathlib.Path.exists") as mock_exists, \
         patch("builtins.open", mock_open(read_data="{invalid_json}")), \
         patch("joblib.load"):
        
        mock_exists.return_value = True
        
        predictor = FraudPredictor()
        with pytest.raises(FraudModelLoadError, match="Failed to parse metadata JSON"):
            predictor.load()


def test_predictor_missing_predict_proba(mock_predictor_dependencies):
    """Test that a model without predict_proba raises FraudModelLoadError."""
    mock_model, mock_preprocessor = mock_predictor_dependencies
    # Remove predict_proba
    del mock_model.predict_proba
    
    predictor = FraudPredictor()
    with pytest.raises(FraudModelLoadError, match="does not support"):
        predictor.load()


def test_predictor_successful_prediction(mock_predictor_dependencies):
    """Test that a valid prediction returns a correct probability score in [0.0, 1.0]."""
    mock_model, mock_preprocessor = mock_predictor_dependencies
    mock_model.predict_proba.return_value = np.array([[0.8, 0.2]]) # positive class is at index 1

    predictor = FraudPredictor()
    predictor.load()
    
    probability = predictor.predict(MOCK_INPUT)
    assert isinstance(probability, float)
    assert 0.0 <= probability <= 1.0
    assert probability == 0.2
    
    # Verify preprocessor and model were called correctly
    mock_preprocessor.transform.assert_called_once()
    mock_model.predict_proba.assert_called_once()


def test_predictor_missing_feature_in_input(mock_predictor_dependencies):
    """Test that missing required feature in input raises FraudModelPredictionError."""
    predictor = FraudPredictor()
    predictor.load()
    
    invalid_input = MOCK_INPUT.copy()
    del invalid_input["Amount"] # Remove required feature
    
    with pytest.raises(FraudModelPredictionError, match="Missing features in record"):
        predictor.predict(invalid_input)


def test_predictor_preprocessor_failure(mock_predictor_dependencies):
    """Test that a failure in the preprocessor transformer is caught and raised as a prediction error."""
    mock_model, mock_preprocessor = mock_predictor_dependencies
    mock_preprocessor.transform.side_effect = ValueError("Corrupted input array format")
    
    predictor = FraudPredictor()
    predictor.load()
    
    with pytest.raises(FraudModelPredictionError, match="Preprocessor transformation failed"):
        predictor.predict(MOCK_INPUT)


def test_predictor_model_prediction_failure(mock_predictor_dependencies):
    """Test that a failure in the classifier inference is caught and raised as a prediction error."""
    mock_model, mock_preprocessor = mock_predictor_dependencies
    mock_model.predict_proba.side_effect = RuntimeError("Inference session failure")
    
    predictor = FraudPredictor()
    predictor.load()
    
    with pytest.raises(FraudModelPredictionError, match="Model predict_proba call failed"):
        predictor.predict(MOCK_INPUT)


def test_service_layer_integration(mock_predictor_dependencies):
    """Test that the FraudPredictionService retrieves predictor, makes predictions, and formats schema results."""
    mock_model, mock_preprocessor = mock_predictor_dependencies
    mock_model.predict_proba.return_value = np.array([[0.6, 0.4]])
    
    # We patch the getter to return a localized loaded predictor rather than loading the global singleton
    local_predictor = FraudPredictor()
    local_predictor.load()
    
    with patch("app.ml.inference.service.get_fraud_predictor", return_value=local_predictor):
        service = FraudPredictionService()
        result = service.predict_transaction(MOCK_INPUT)
        
        assert result.probability == 0.4
        # Since threshold is 0.35 and prob is 0.4, is_fraud should be True
        assert result.is_fraud is True
        assert result.threshold == 0.35
        assert result.model_version == "1.0.0-test"
        assert result.model_name == "HistGradientBoostingClassifier"


def test_service_prediction_failure_controlled(mock_predictor_dependencies):
    """Test that failures in the predictor are propagated as controlled errors from service layer."""
    mock_model, mock_preprocessor = mock_predictor_dependencies
    mock_preprocessor.transform.side_effect = ValueError("Preprocessor error")
    
    local_predictor = FraudPredictor()
    local_predictor.load()
    
    with patch("app.ml.inference.service.get_fraud_predictor", return_value=local_predictor):
        service = FraudPredictionService()
        with pytest.raises(FraudModelPredictionError, match="Preprocessor transformation failed"):
            service.predict_transaction(MOCK_INPUT)


from app.ml.inference.risk_classifier import FraudRiskClassifier, FraudRiskLevel

def test_risk_classification_low_medium_high():
    # medium threshold: 0.40, high threshold: 0.70
    classifier = FraudRiskClassifier(medium_threshold=0.40, high_threshold=0.70)
    
    # 1. LOW risk classification
    assert classifier.classify(0.10) == FraudRiskLevel.LOW
    assert classifier.classify(0.39) == FraudRiskLevel.LOW
    
    # 2. MEDIUM risk classification
    assert classifier.classify(0.45) == FraudRiskLevel.MEDIUM
    assert classifier.classify(0.69) == FraudRiskLevel.MEDIUM
    
    # 3. HIGH risk classification
    assert classifier.classify(0.75) == FraudRiskLevel.HIGH
    assert classifier.classify(1.0) == FraudRiskLevel.HIGH
    
    # 4. Probability exactly at medium threshold
    assert classifier.classify(0.40) == FraudRiskLevel.MEDIUM
    
    # 5. Probability exactly at high threshold
    assert classifier.classify(0.70) == FraudRiskLevel.HIGH


def test_service_probability_boundary_checks(mock_predictor_dependencies):
    """Test probability mapping against binary fraud threshold and independence from risk levels."""
    mock_model, mock_preprocessor = mock_predictor_dependencies
    
    # Threshold in MOCK_METADATA is 0.35, risk medium is 0.40 (fallback), high is 0.70 (fallback)
    local_predictor = FraudPredictor()
    local_predictor.load()
    
    with patch("app.ml.inference.service.get_fraud_predictor", return_value=local_predictor):
        service = FraudPredictionService()
        
        # 6. Probability exactly at fraud classification threshold (0.35)
        # is_fraud should be True, risk should be LOW (0.35 < 0.40)
        mock_model.predict_proba.return_value = np.array([[0.65, 0.35]])
        res = service.predict_transaction(MOCK_INPUT)
        assert res.is_fraud is True
        assert res.risk_level == FraudRiskLevel.LOW
        
        # 7. Probability below fraud classification threshold (0.34)
        # is_fraud should be False, risk should be LOW
        mock_model.predict_proba.return_value = np.array([[0.66, 0.34]])
        res = service.predict_transaction(MOCK_INPUT)
        assert res.is_fraud is False
        assert res.risk_level == FraudRiskLevel.LOW
        
        # 8. Probability above fraud classification threshold (0.36)
        # is_fraud should be True, risk should be LOW
        mock_model.predict_proba.return_value = np.array([[0.64, 0.36]])
        res = service.predict_transaction(MOCK_INPUT)
        assert res.is_fraud is True
        assert res.risk_level == FraudRiskLevel.LOW

        # 9. is_fraud is independent from risk_level:
        # threshold is 0.35, medium threshold is 0.40
        # 0.38 >= 0.35 (is_fraud=True), but 0.38 < 0.40 (risk_level=LOW)
        mock_model.predict_proba.return_value = np.array([[0.62, 0.38]])
        res = service.predict_transaction(MOCK_INPUT)
        assert res.is_fraud is True
        assert res.risk_level == FraudRiskLevel.LOW

        # prob=0.50: is_fraud=True, risk_level=MEDIUM
        mock_model.predict_proba.return_value = np.array([[0.50, 0.50]])
        res = service.predict_transaction(MOCK_INPUT)
        assert res.is_fraud is True
        assert res.risk_level == FraudRiskLevel.MEDIUM


def test_service_probability_invalid_values(mock_predictor_dependencies):
    """Test that invalid float probability values raise FraudModelPredictionError."""
    mock_model, mock_preprocessor = mock_predictor_dependencies
    local_predictor = FraudPredictor()
    local_predictor.load()
    
    with patch("app.ml.inference.service.get_fraud_predictor", return_value=local_predictor):
        service = FraudPredictionService()
        
        # 10. Invalid NaN probability raises controlled error
        mock_model.predict_proba.return_value = np.array([[0.5, float("nan")]])
        with pytest.raises(FraudModelPredictionError, match="Invalid prediction probability"):
            service.predict_transaction(MOCK_INPUT)
            
        # 11. Invalid infinite probability raises controlled error
        mock_model.predict_proba.return_value = np.array([[0.5, float("inf")]])
        with pytest.raises(FraudModelPredictionError, match="Invalid prediction probability"):
            service.predict_transaction(MOCK_INPUT)
            
        # 12. Negative probability raises controlled error
        mock_model.predict_proba.return_value = np.array([[1.5, -0.5]])
        with pytest.raises(FraudModelPredictionError, match="Invalid prediction probability"):
            service.predict_transaction(MOCK_INPUT)
            
        # 13. Probability > 1.0 raises controlled error
        mock_model.predict_proba.return_value = np.array([[-0.5, 1.5]])
        with pytest.raises(FraudModelPredictionError, match="Invalid prediction probability"):
            service.predict_transaction(MOCK_INPUT)


def test_risk_threshold_validation_errors():
    """Test that invalid risk thresholds raise FraudModelLoadError."""
    # 14. Invalid risk threshold ordering (medium >= high) raises controlled error
    with pytest.raises(FraudModelLoadError, match="must be strictly less than"):
        FraudRiskClassifier(medium_threshold=0.60, high_threshold=0.50)
        
    with pytest.raises(FraudModelLoadError, match="must be strictly less than"):
        FraudRiskClassifier(medium_threshold=0.50, high_threshold=0.50)
        
    # 15. Invalid risk threshold range (out of [0.0, 1.0]) raises controlled error
    with pytest.raises(FraudModelLoadError, match="is outside"):
        FraudRiskClassifier(medium_threshold=-0.1, high_threshold=0.5)
        
    with pytest.raises(FraudModelLoadError, match="is outside"):
        FraudRiskClassifier(medium_threshold=0.5, high_threshold=1.1)


def test_metadata_and_model_version_inclusion(mock_predictor_dependencies):
    """Test that the prediction result correctly includes model version and name fields."""
    mock_model, mock_preprocessor = mock_predictor_dependencies
    local_predictor = FraudPredictor()
    local_predictor.load()
    
    with patch("app.ml.inference.service.get_fraud_predictor", return_value=local_predictor):
        service = FraudPredictionService()
        
        # 16. Model version and name are correctly included
        res = service.predict_transaction(MOCK_INPUT)
        assert res.model_version == "1.0.0-test"
        assert res.model_name == "HistGradientBoostingClassifier"
        assert res.fraud_probability == 0.2
        assert res.probability == 0.2
        assert res.threshold == 0.35

