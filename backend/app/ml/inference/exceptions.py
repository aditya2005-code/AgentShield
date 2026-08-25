class FraudInferenceError(Exception):
    """Base exception for all fraud ML inference errors."""
    pass

class FraudModelArtifactNotFoundError(FraudInferenceError):
    """Raised when one or more fraud model artifacts cannot be found on disk."""
    pass

class FraudModelLoadError(FraudInferenceError):
    """Raised when loading or validating a model artifact fails."""
    pass

class FraudModelPredictionError(FraudInferenceError):
    """Raised when preprocessing or model prediction fails."""
    pass
