import json
import logging
import threading
from pathlib import Path
from typing import Any, Dict, List, Union

import joblib
import pandas as pd

from app.core.config import settings
from app.ml.inference.exceptions import (
    FraudModelArtifactNotFoundError,
    FraudModelLoadError,
    FraudModelPredictionError,
)

logger = logging.getLogger(__name__)

REQUIRED_FEATURES = [
    "Amount",
    "Merchant_Category",
    "Distance_from_Home",
    "Device_Type",
    "IP_Risk_Score",
    "Avg_Spending_Habit",
    "Is_Weekend",
    "Is_Night_Transaction",
    "Transaction_Hour",
    "Day_of_Week",
]


class FraudPredictor:
    """
    Handles locating, validating, caching, and executing predictions
    for the trained Fraud ML model and preprocessor.
    """

    def __init__(self):
        self._model = None
        self._preprocessor = None
        self._metadata = None
        self._is_loaded = False
        self._load_lock = threading.Lock()
        self._positive_class_index = 1

    def load(self) -> None:
        """
        Loads and validates the model, preprocessor, and metadata artifacts.
        Subsequent calls are no-ops due to in-memory caching.
        """
        if self._is_loaded:
            return

        with self._load_lock:
            if self._is_loaded:
                return

            logger.info("Initializing Fraud ML model loading...")

            # 1. Resolve and validate paths
            try:
                model_path_str = settings.resolve_ml_path(settings.FRAUD_MODEL_PATH)
                preprocessor_path_str = settings.resolve_ml_path(settings.FRAUD_PREPROCESSOR_PATH)
                metadata_path_str = settings.resolve_ml_path(settings.FRAUD_METADATA_PATH)
            except Exception as e:
                logger.error(f"Error resolving artifact paths: {e}")
                raise FraudModelArtifactNotFoundError(f"Failed to resolve artifact paths: {e}")

            model_path = Path(model_path_str)
            preprocessor_path = Path(preprocessor_path_str)
            metadata_path = Path(metadata_path_str)

            # Check existence of files
            missing_files = []
            if not model_path.exists():
                missing_files.append(str(model_path))
            if not preprocessor_path.exists():
                missing_files.append(str(preprocessor_path))
            if not metadata_path.exists():
                missing_files.append(str(metadata_path))

            if missing_files:
                err_msg = f"Missing ML artifact files: {', '.join(missing_files)}"
                logger.error(err_msg)
                raise FraudModelArtifactNotFoundError(err_msg)

            # 2. Load model_metadata.json
            try:
                with open(metadata_path, "r", encoding="utf-8") as f:
                    self._metadata = json.load(f)
            except json.JSONDecodeError as e:
                err_msg = f"Failed to parse metadata JSON from {metadata_path}: {e}"
                logger.error(err_msg)
                raise FraudModelLoadError(err_msg)
            except Exception as e:
                err_msg = f"Failed to read metadata from {metadata_path}: {e}"
                logger.error(err_msg)
                raise FraudModelLoadError(err_msg)

            # Validate basic metadata structure
            required_meta_keys = ["model_name", "model_version", "prediction"]
            for key in required_meta_keys:
                if key not in self._metadata:
                    err_msg = f"Invalid model metadata: missing required key '{key}'"
                    logger.error(err_msg)
                    raise FraudModelLoadError(err_msg)

            # 3. Load model and preprocessor joblib files
            try:
                self._model = joblib.load(model_path)
            except Exception as e:
                err_msg = f"Failed to unpickle model from {model_path}: {e}"
                logger.error(err_msg)
                raise FraudModelLoadError(err_msg)

            try:
                self._preprocessor = joblib.load(preprocessor_path)
            except Exception as e:
                err_msg = f"Failed to unpickle preprocessor from {preprocessor_path}: {e}"
                logger.error(err_msg)
                raise FraudModelLoadError(err_msg)

            # 4. Validate artifact capabilities and compatibility
            if not hasattr(self._model, "predict_proba"):
                err_msg = "Model loaded successfully but does not support 'predict_proba()'."
                logger.error(err_msg)
                raise FraudModelLoadError(err_msg)

            # Determine positive class index
            classes = list(getattr(self._model, "classes_", []))
            if classes:
                try:
                    # Target value 1 indicates fraud class
                    self._positive_class_index = classes.index(1)
                except ValueError:
                    self._positive_class_index = self._metadata.get("prediction", {}).get("probability_index", 1)
            else:
                self._positive_class_index = self._metadata.get("prediction", {}).get("probability_index", 1)

            self._is_loaded = True
            logger.info(
                f"Fraud ML model loaded successfully. Model: {self._metadata['model_name']}, "
                f"Version: {self._metadata['model_version']}, "
                f"Threshold: {self._metadata['prediction'].get('fraud_classification_threshold', 0.25)}"
            )

    def is_loaded(self) -> bool:
        """Returns True if the artifacts are currently loaded in-memory."""
        return self._is_loaded

    def get_metadata(self) -> Dict[str, Any]:
        """Returns the loaded model metadata dict."""
        if not self._is_loaded:
            raise FraudModelLoadError("Model is not loaded. Call load() first.")
        return self._metadata

    def get_model_info(self) -> Dict[str, Any]:
        """Returns safe, clean public model information."""
        meta = self.get_metadata()
        pred = meta.get("prediction", {})
        return {
            "model_name": meta.get("model_name"),
            "model_version": meta.get("model_version"),
            "fraud_classification_threshold": pred.get("fraud_classification_threshold", 0.25),
            "model_iterations": meta.get("model_iterations"),
            "created_at_utc": meta.get("created_at_utc"),
        }

    def predict(self, raw_input: Union[Dict[str, Any], List[Dict[str, Any]]]) -> Union[float, List[float]]:
        """
        Runs prediction for the given raw transaction features.
        Preserves original features order, executes ColumnTransformer preprocessing,
        runs model inference, and extracts positive-class probability.

        Args:
            raw_input: A dictionary of features or a list of feature dictionaries.

        Returns:
            A single float probability of fraud, or a list of probabilities if input was a list.
        """
        if not self._is_loaded:
            self.load()

        is_single = isinstance(raw_input, dict)
        inputs = [raw_input] if is_single else raw_input

        # 1. Feature verification and DataFrame construction
        records = []
        for i, inp in enumerate(inputs):
            missing_features = [f for f in REQUIRED_FEATURES if f not in inp]
            if missing_features:
                err_msg = f"Missing features in record {i}: {', '.join(missing_features)}"
                logger.error(err_msg)
                raise FraudModelPredictionError(err_msg)
            
            # Keep only REQUIRED_FEATURES and maintain feature order
            records.append({feat: inp[feat] for feat in REQUIRED_FEATURES})

        try:
            df = pd.DataFrame(records)
        except Exception as e:
            err_msg = f"Failed to construct Pandas DataFrame: {e}"
            logger.error(err_msg)
            raise FraudModelPredictionError(err_msg)

        # 2. Preprocessor transformation
        try:
            X_transformed = self._preprocessor.transform(df)
        except Exception as e:
            err_msg = f"Preprocessor transformation failed: {e}"
            logger.error(err_msg)
            raise FraudModelPredictionError(err_msg)

        # 3. Model inference
        try:
            probabilities = self._model.predict_proba(X_transformed)
        except Exception as e:
            err_msg = f"Model predict_proba call failed: {e}"
            logger.error(err_msg)
            raise FraudModelPredictionError(err_msg)

        # 4. Extract positive class probabilities
        try:
            positive_class_probs = probabilities[:, self._positive_class_index].tolist()
        except Exception as e:
            err_msg = f"Failed to extract positive class probabilities: {e}"
            logger.error(err_msg)
            raise FraudModelPredictionError(err_msg)

        return positive_class_probs[0] if is_single else positive_class_probs


# Singleton management
_predictor_instance = None
_predictor_lock = threading.Lock()


def get_fraud_predictor() -> FraudPredictor:
    """Returns the loaded singleton instance of FraudPredictor."""
    global _predictor_instance
    if _predictor_instance is None:
        with _predictor_lock:
            if _predictor_instance is None:
                predictor = FraudPredictor()
                predictor.load()
                _predictor_instance = predictor
    return _predictor_instance
