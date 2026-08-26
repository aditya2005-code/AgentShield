import logging
from fastapi import APIRouter, status
from app.ml.inference.service import FraudPredictionService, FraudPredictionResult
from app.schemas.fraud import FraudPredictionRequest

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/fraud", tags=["Fraud Prediction"])

# Expose the API endpoint and reuse the underlying thread-safe cached predictor
fraud_service = FraudPredictionService()


@router.post(
    "/predict",
    response_model=FraudPredictionResult,
    status_code=status.HTTP_200_OK,
    summary="Generate fraud risk classification for a transaction",
    description="This endpoint returns an ML-generated fraud risk signal. It does not independently approve or reject a transaction. Final decision authority remains with AgentShield."
)
def predict_fraud(payload: FraudPredictionRequest) -> FraudPredictionResult:
    """
    Evaluates transaction features using the trained ML model and returns a structured fraud signal.
    """
    logger.info("Received request for fraud prediction")
    
    # payload.model_dump() contains the exact 10 features corresponding to the model request schema
    features = payload.model_dump()
    result = fraud_service.predict_transaction(features)
    
    logger.info(
        f"Fraud prediction completed. Probability: {result.fraud_probability:.4f}, "
        f"Risk Level: {result.risk_level}, Is Fraud: {result.is_fraud}"
    )
    return result
