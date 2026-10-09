"""APK XGBoost classifier provider."""

from __future__ import annotations

import os
from pathlib import Path
from typing import Any
from uuid import UUID

from app.contracts.status import AnalysisStatus


FEATURE_NAMES = (
    "permission_count",
    "high_risk_permission_count",
    "sms_permission_indicator",
    "authentication_permission_indicator",
    "activity_count",
    "service_count",
    "receiver_count",
    "provider_count",
    "min_sdk",
    "target_sdk",
    "legacy_target_sdk_indicator",
    "certificate_count",
    "signature_scheme_count",
    "dex_count",
    "native_library_count",
    "native_library_indicator",
    "resource_indicator",
    "certificate_directory_indicator",
)


class APKClassifier:
    """Optional XGBoost classifier for APK static features."""

    provider_name = "apk_xgboost_classifier"
    version = "1.0.0"
    is_available = True

    def __init__(self, model_path: str | None = None) -> None:
        self.model_path = model_path or os.getenv(
            "VERA_APK_XGB_MODEL_PATH"
        )
        self._model: Any | None = None

    async def health_check(self) -> dict[str, Any]:
        """Report classifier availability."""

        if not self.is_available:
            return {
                "status": AnalysisStatus.UNAVAILABLE.value,
                "is_available": False,
                "provider": self.provider_name,
                "version": self.version,
            }

        if not self.model_path:
            return {
                "status": AnalysisStatus.UNAVAILABLE.value,
                "is_available": False,
                "provider": self.provider_name,
                "version": self.version,
                "error": "APK XGBoost model artifact is not configured.",
            }

        model_path = Path(self.model_path)

        if not model_path.is_file():
            return {
                "status": AnalysisStatus.UNAVAILABLE.value,
                "is_available": False,
                "provider": self.provider_name,
                "version": self.version,
                "error": (
                    "APK XGBoost model artifact was not found: "
                    f"{model_path}"
                ),
            }

        return {
            "status": AnalysisStatus.SUCCESS.value,
            "is_available": True,
            "provider": self.provider_name,
            "version": self.version,
        }

    async def analyze_apk(
        self,
        investigation_id: UUID,
        apk_bytes: bytes,
    ) -> dict[str, Any]:
        """Analyze raw APK bytes.

        Raw APK parsing is intentionally outside this classifier.
        Classification requires the deterministic static feature vector
        and a configured XGBoost model artifact.
        """

        if not self.is_available:
            return {
                "status": AnalysisStatus.UNAVAILABLE.value,
                "investigation_id": str(investigation_id),
                "prediction": None,
                "model_score": None,
                "risk_score": None,
                "error": (
                    "APK XGBoost classifier is unavailable because no "
                    "model artifact is configured."
                ),
            }

        if not apk_bytes:
            return {
                "status": AnalysisStatus.INSUFFICIENT_EVIDENCE.value,
                "investigation_id": str(investigation_id),
                "prediction": None,
                "model_score": None,
                "risk_score": None,
                "error": "APK bytes are empty.",
            }

        return {
            "status": AnalysisStatus.UNAVAILABLE.value,
            "investigation_id": str(investigation_id),
            "prediction": None,
            "model_score": None,
            "risk_score": None,
            "error": (
                "APK XGBoost model artifact is not configured. "
                "Raw APK bytes were not classified."
            ),
        }

    async def classify(
        self,
        feature_vector: dict[str, Any],
    ) -> dict[str, Any]:
        """Classify an APK feature vector."""

        validation_error = self._validate_features(feature_vector)

        if validation_error:
            return {
                "status": AnalysisStatus.FAILED.value,
                "prediction": None,
                "model_score": None,
                "model_version": None,
                "feature_count": len(feature_vector),
                "error": validation_error,
            }

        if not self.model_path:
            return self._unavailable(
                "APK XGBoost model artifact is not configured."
            )

        model_path = Path(self.model_path)

        if not model_path.is_file():
            return self._unavailable(
                f"APK XGBoost model artifact was not found: {model_path}"
            )

        try:
            model = self._load_model(model_path)

            values = [
                float(feature_vector[name])
                for name in FEATURE_NAMES
            ]

            prediction = model.predict([values])[0]

            model_score = None

            if hasattr(model, "predict_proba"):
                probabilities = model.predict_proba([values])

                if probabilities is not None:
                    model_score = float(max(probabilities[0]))

            return {
                "status": AnalysisStatus.SUCCESS.value,
                "prediction": self._normalize_prediction(prediction),
                "model_score": model_score,
                "model_version": self.version,
                "feature_count": len(FEATURE_NAMES),
                "feature_names": list(FEATURE_NAMES),
            }

        except Exception as exc:
            return {
                "status": AnalysisStatus.FAILED.value,
                "prediction": None,
                "model_score": None,
                "model_version": None,
                "feature_count": len(FEATURE_NAMES),
                "error": f"APK XGBoost classification failed: {exc}",
            }

    def _load_model(self, model_path: Path) -> Any:
        if self._model is not None:
            return self._model

        try:
            from xgboost import XGBClassifier
        except ImportError as exc:
            raise RuntimeError(
                "XGBoost is not installed."
            ) from exc

        model = XGBClassifier()
        model.load_model(str(model_path))

        self._model = model

        return model

    @staticmethod
    def _validate_features(
        feature_vector: dict[str, Any],
    ) -> str | None:
        expected = set(FEATURE_NAMES)
        actual = set(feature_vector)

        missing = expected - actual

        if missing:
            return (
                "APK feature vector is missing required features: "
                + ", ".join(sorted(missing))
            )

        extra = actual - expected

        if extra:
            return (
                "APK feature vector contains unexpected features: "
                + ", ".join(sorted(extra))
            )

        for name in FEATURE_NAMES:
            if feature_vector[name] is None:
                return f"APK feature '{name}' cannot be None."

        return None

    @staticmethod
    def _normalize_prediction(prediction: Any) -> Any:
        if hasattr(prediction, "item"):
            return prediction.item()

        return prediction

    @staticmethod
    def _unavailable(error: str) -> dict[str, Any]:
        return {
            "status": AnalysisStatus.UNAVAILABLE.value,
            "prediction": None,
            "model_score": None,
            "model_version": None,
            "feature_count": 0,
            "error": error,
        }


class UnavailableAPKClassifier(APKClassifier):
    """Explicit unavailable classifier implementation."""

    is_available = False

    async def health_check(self) -> dict[str, Any]:
        """Report unavailable classifier health."""

        return {
            "status": AnalysisStatus.UNAVAILABLE.value,
            "is_available": False,
            "provider": self.provider_name,
            "version": self.version,
            "error": (
                "APK XGBoost classifier is unavailable because no model "
                "artifact is configured."
            ),
        }

    async def analyze_apk(
        self,
        investigation_id: UUID,
        apk_bytes: bytes,
    ) -> dict[str, Any]:
        """Return explicit unavailable status."""

        return {
            "status": AnalysisStatus.UNAVAILABLE.value,
            "investigation_id": str(investigation_id),
            "prediction": None,
            "model_score": None,
            "risk_score": None,
            "error": (
                "APK XGBoost classifier is unavailable because no model "
                "artifact is configured."
            ),
        }

    async def classify(
        self,
        feature_vector: dict[str, Any],
    ) -> dict[str, Any]:
        """Return explicit unavailable status."""

        return self._unavailable(
            "APK XGBoost classifier is unavailable because no model "
            "artifact is configured."
        )