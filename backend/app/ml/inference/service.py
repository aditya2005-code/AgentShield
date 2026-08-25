import logging
import math
from pydantic import BaseModel, Field

from app.ml.inference.predictor import get_fraud_predictor
from app.ml.inference.exceptions import FraudModelPredictionError, FraudModelLoadError
from app.ml.inference.risk_classifier import FraudRiskLevel

logger = logging.getLogger(__name__)


class FraudPredictionResult(BaseModel):
    """
    Standard schema representing the result of a fraud ML model prediction.
    Contains the probability, final binary decision based on metadata threshold,
    risk level classification, and associated model identifiers.
    """
    fraud_probability: float = Field(
        ...,
        description="The positive-class fraud probability from the classifier (0.0 to 1.0)"
    )
    probability: float = Field(
        ..., 
        description="The positive-class fraud probability from the classifier (0.0 to 1.0). Kept for backward compatibility."
    )
    risk_level: FraudRiskLevel = Field(
        ...,
        description="The classified risk severity level (LOW, MEDIUM, HIGH)"
    )
    is_fraud: bool = Field(
        ..., 
        description="Binary decision: True if probability >= classification threshold, else False"
    )
    threshold: float = Field(
        ..., 
        description="The classification threshold retrieved from model metadata"
    )
    model_version: str = Field(
        ..., 
        description="The version string of the model used for inference"
    )
    model_name: str = Field(
        ..., 
        description="The name of the classifier used for inference"
    )


class FraudPredictionService:
    """
    A service wrapper around the FraudPredictor that exposes standard
    prediction operations and models response schema.
    """

    def __init__(self):
        # Initializes and lazy-loads the predictor singleton
        self._predictor = get_fraud_predictor()

    def predict_transaction(self, features: dict) -> FraudPredictionResult:
        """
        Processes transaction features and determines the likelihood of fraud.
        Validates output matches the required schema boundaries and classifies risk.

        Args:
            features: Dictionary containing transaction and customer features.

        Returns:
            A FraudPredictionResult object.
        """
        try:
            probability = self._predictor.predict(features)
            
            # Since features could be a list (batch), handle list result if necessary,
            # but predict_transaction is designed for single transaction evaluation.
            if isinstance(probability, list):
                raise FraudModelPredictionError("Batch predictions are not supported in predict_transaction.")
                
            # Validate output probability boundaries
            if not isinstance(probability, (int, float)) or math.isnan(probability) or math.isinf(probability) or not (0.0 <= probability <= 1.0):
                err_msg = f"Invalid prediction probability: {probability} must be a finite float in [0.0, 1.0]"
                logger.error(err_msg)
                raise FraudModelPredictionError(err_msg)

            metadata = self._predictor.get_metadata()
            threshold = metadata.get("prediction", {}).get("fraud_classification_threshold", 0.25)
            is_fraud = probability >= threshold

            # Classify risk level using startup-validated classifier
            risk_classifier = self._predictor.get_risk_classifier()
            risk_level = risk_classifier.classify(probability)

            return FraudPredictionResult(
                fraud_probability=probability,
                probability=probability,
                risk_level=risk_level,
                is_fraud=is_fraud,
                threshold=threshold,
                model_version=metadata.get("model_version", "1.0.0"),
                model_name=metadata.get("model_name", "HistGradientBoostingClassifier")
            )
        except Exception as e:
            # Avoid exposing internal stack traces but log the failure details internally
            logger.error(f"Inference execution failed in service layer: {e}")
            if isinstance(e, (FraudModelPredictionError, FraudModelLoadError, ValueError)):
                raise e
            raise FraudModelPredictionError(f"Prediction failed in service layer: {e}")
