"""
Fraud Risk Level Classification

This module provides deterministic, threshold-based risk categorisation for
fraud probability scores produced by the ML model.

Concepts:
---------
* fraud_classification_threshold (from model metadata):
    Controls the *binary* is_fraud decision.
    Example: probability >= 0.25  →  is_fraud = True

* risk_thresholds.medium / risk_thresholds.high (from model metadata):
    Control severity categorisation, independent of is_fraud.
    Example:
        probability < 0.40  →  LOW
        0.40 <= probability < 0.70  →  MEDIUM
        probability >= 0.70  →  HIGH

Risk level and is_fraud are intentionally separate concepts.
A transaction can be is_fraud=True but only MEDIUM risk (e.g. probability 0.30),
and is_fraud=False but MEDIUM risk would never occur given threshold 0.25.
"""

import logging
from enum import Enum
from typing import Dict, Any

from app.ml.inference.exceptions import FraudModelLoadError

logger = logging.getLogger(__name__)

# Fallback defaults when metadata does not supply risk_thresholds
_DEFAULT_MEDIUM_THRESHOLD = 0.40
_DEFAULT_HIGH_THRESHOLD = 0.70


class FraudRiskLevel(str, Enum):
    """
    Categorical risk severity for a fraud probability score.

    LOW    — probability below the medium threshold
    MEDIUM — probability in [medium_threshold, high_threshold)
    HIGH   — probability at or above the high threshold
    """
    LOW = "LOW"
    MEDIUM = "MEDIUM"
    HIGH = "HIGH"


class FraudRiskClassifier:
    """
    Classifies a validated fraud probability score into a FraudRiskLevel.

    Thresholds are loaded from model metadata at instantiation and validated
    immediately — no silent fallbacks for invalid configurations.

    Usage:
        classifier = FraudRiskClassifier.from_metadata(metadata_dict)
        level = classifier.classify(0.55)  # → FraudRiskLevel.MEDIUM
    """

    def __init__(self, medium_threshold: float, high_threshold: float) -> None:
        self._medium = medium_threshold
        self._high = high_threshold
        self._validate()

    def _validate(self) -> None:
        """Raises FraudModelLoadError for any invalid threshold configuration."""
        errors = []
        if not (0.0 <= self._medium <= 1.0):
            errors.append(
                f"medium threshold {self._medium} is outside [0.0, 1.0]"
            )
        if not (0.0 <= self._high <= 1.0):
            errors.append(
                f"high threshold {self._high} is outside [0.0, 1.0]"
            )
        if self._medium >= self._high:
            errors.append(
                f"medium threshold {self._medium} must be strictly less than "
                f"high threshold {self._high}"
            )
        if errors:
            msg = "Invalid risk threshold configuration: " + "; ".join(errors)
            logger.error(msg)
            raise FraudModelLoadError(msg)

    @classmethod
    def from_metadata(cls, prediction_section: Dict[str, Any]) -> "FraudRiskClassifier":
        """
        Constructs a FraudRiskClassifier from the 'prediction' block of
        model_metadata.json.

        Falls back to module-level defaults when 'risk_thresholds' is absent,
        so older metadata files continue to work.
        """
        risk = prediction_section.get("risk_thresholds", {})
        medium = risk.get("medium", _DEFAULT_MEDIUM_THRESHOLD)
        high = risk.get("high", _DEFAULT_HIGH_THRESHOLD)
        logger.info(
            f"Initialising FraudRiskClassifier: medium={medium}, high={high}"
        )
        return cls(medium_threshold=medium, high_threshold=high)

    @property
    def medium_threshold(self) -> float:
        return self._medium

    @property
    def high_threshold(self) -> float:
        return self._high

    def classify(self, probability: float) -> FraudRiskLevel:
        """
        Maps a validated probability in [0.0, 1.0] to a FraudRiskLevel.

        This method is deterministic and side-effect free — suitable for
        direct unit testing.

        Args:
            probability: Fraud probability output from predict_proba, already
                         validated to be a finite float in [0.0, 1.0].

        Returns:
            FraudRiskLevel enum member.
        """
        if probability >= self._high:
            return FraudRiskLevel.HIGH
        if probability >= self._medium:
            return FraudRiskLevel.MEDIUM
        return FraudRiskLevel.LOW
