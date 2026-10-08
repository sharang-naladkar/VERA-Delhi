"""APK risk classification providers."""

from __future__ import annotations

from typing import Any

from app.contracts.status import AnalysisStatus
from app.providers.apk_analyzer import APKAnalyzer
from app.providers.apk_feature_extractor import APKFeatureExtractor
from app.providers.apk_static_analyzer import APKStaticAnalyzer
from app.providers.base import BaseProvider


class APKClassifier(BaseProvider):
    """Base interface for APK risk classifiers."""

    provider_name = "apk_classifier"
    version = "1.0.0"
    is_available = True

    async def health_check(self) -> dict[str, Any]:
        return {
            "status": (
                AnalysisStatus.SUCCESS.value
                if self.is_available
                else AnalysisStatus.UNAVAILABLE.value
            ),
            "provider": self.provider_name,
            "version": self.version,
            "available": self.is_available,
        }

    async def analyze_apk(
        self,
        investigation_id: Any,
        apk_bytes: bytes,
    ) -> dict[str, Any]:
        raise NotImplementedError


class UnavailableAPKClassifier(APKClassifier):
    """Fallback classifier used when no APK classifier is available."""

    provider_name = "unavailable_apk_classifier"
    version = "1.0.0"
    is_available = False

    async def health_check(self) -> dict[str, Any]:
        return {
            "status": AnalysisStatus.UNAVAILABLE.value,
            "provider": self.provider_name,
            "version": self.version,
            "available": False,
        }

    async def analyze_apk(
        self,
        investigation_id: Any,
        apk_bytes: bytes,
    ) -> dict[str, Any]:
        return {
            "status": AnalysisStatus.UNAVAILABLE.value,
            "provider": self.provider_name,
            "version": self.version,
            "investigation_id": investigation_id,
            "package_name": None,
            "risk_score": None,
            "risk_level": None,
            "error": (
                "APK classifier provider is unavailable."
            ),
        }


class DrebinAPKClassifier(APKClassifier):
    """Deterministic Drebin-style heuristic APK classifier.

    This provider is intentionally not a trained statistical model.
    It produces a deterministic risk signal from extracted APK features.
    """

    provider_name = "drebin_heuristic_classifier"
    version = "1.0.0"
    is_available = True

    FEATURE_WEIGHTS: dict[str, float] = {
        "has_sms_api": 0.16,
        "has_telephony_api": 0.08,
        "has_accessibility_api": 0.15,
        "has_device_admin_api": 0.15,
        "has_dynamic_code_loading": 0.12,
        "has_dynamic_class_loading": 0.10,
        "has_runtime_api": 0.05,
        "has_package_manager_api": 0.05,
        "has_clipboard_api": 0.05,
        "has_camera_api": 0.03,
        "has_audio_record_api": 0.03,
        "has_device_information_api": 0.06,
        "has_location_api": 0.04,
        "has_network_api": 0.03,
        "has_webview_api": 0.04,
        "has_http_api": 0.04,
        "has_url_api": 0.03,
        "has_tls_api": 0.01,
        "has_short_class_reference": 0.06,
        "has_short_package_reference": 0.05,
        "has_base64_reference": 0.07,
        "has_xor_reference": 0.08,
        "has_high_short_string_ratio": 0.08,
        "native_library_count": 0.03,
        "suspicious_entry_count": 0.08,
    }

    COUNT_FEATURES = {
        "native_library_count",
        "suspicious_entry_count",
    }

    def __init__(
        self,
        analyzer: APKAnalyzer | None = None,
        static_analyzer: APKStaticAnalyzer | None = None,
        feature_extractor: APKFeatureExtractor | None = None,
    ) -> None:
        self.analyzer = analyzer or APKAnalyzer()
        self.static_analyzer = (
            static_analyzer or APKStaticAnalyzer()
        )
        self.feature_extractor = (
            feature_extractor or APKFeatureExtractor()
        )

    async def analyze_apk(
        self,
        investigation_id: Any,
        apk_bytes: bytes,
    ) -> dict[str, Any]:
        """Analyze an APK from raw bytes."""

        if not apk_bytes:
            return {
                "status": (
                    AnalysisStatus.INSUFFICIENT_EVIDENCE.value
                ),
                "provider": self.provider_name,
                "version": self.version,
                "investigation_id": investigation_id,
                "package_name": None,
                "risk_score": None,
                "risk_level": None,
                "feature_names": [],
                "feature_vector": [],
                "matched_features": [],
                "error": "APK bytes are empty.",
            }

        structural_result = self.analyzer.analyze(
            apk_bytes=apk_bytes,
        )

        if not structural_result.get("is_valid"):
            return {
                "status": AnalysisStatus.FAILED.value,
                "provider": self.provider_name,
                "version": self.version,
                "investigation_id": investigation_id,
                "package_name": None,
                "risk_score": None,
                "risk_level": None,
                "feature_names": [],
                "feature_vector": [],
                "matched_features": [],
                "structural_analysis": structural_result,
                "error": (
                    "APK structural validation failed."
                ),
            }

        static_result = self.static_analyzer.analyze(
            apk_bytes,
        )

        feature_result = self.feature_extractor.extract(
            structural_result=structural_result,
            static_result=static_result,
        )

        classification = self.classify_features(
            feature_result
        )

        return {
            "status": AnalysisStatus.SUCCESS.value,
            "provider": self.provider_name,
            "version": self.version,
            "investigation_id": investigation_id,
            "package_name": None,
            "risk_score": classification["risk_score"],
            "risk_level": classification["risk_level"],
            "feature_names": classification[
                "feature_names"
            ],
            "feature_vector": classification[
                "feature_vector"
            ],
            "matched_features": classification[
                "matched_features"
            ],
            "structural_analysis": structural_result,
            "static_analysis": static_result,
            "feature_extraction": feature_result,
            "classification": classification,
        }

    def classify_features(
        self,
        feature_result: dict[str, Any],
    ) -> dict[str, Any]:
        """Classify an already-extracted APK feature result."""

        features = feature_result.get("features")

        if not isinstance(features, dict):
            features = {}

        risk_score = self._calculate_risk(features)
        risk_level = self._risk_level(risk_score)

        matched_features: list[dict[str, Any]] = []

        for feature_name, weight in self.FEATURE_WEIGHTS.items():
            raw_value = features.get(feature_name, 0)

            if feature_name in self.COUNT_FEATURES:
                try:
                    value = max(
                        0.0,
                        float(raw_value),
                    )
                except (TypeError, ValueError):
                    value = 0.0

                contribution = (
                    min(value, 3.0) * weight
                )
            else:
                if isinstance(raw_value, bool):
                    value = (
                        1.0
                        if raw_value
                        else 0.0
                    )
                else:
                    try:
                        value = float(raw_value)
                    except (TypeError, ValueError):
                        value = 0.0

                value = 1.0 if value > 0 else 0.0
                contribution = value * weight

            if contribution > 0:
                matched_features.append(
                    {
                        "feature": feature_name,
                        "value": raw_value,
                        "weight": weight,
                        "contribution": round(
                            contribution,
                            6,
                        ),
                    }
                )

        matched_features.sort(
            key=lambda item: item["contribution"],
            reverse=True,
        )

        return {
            "provider": self.provider_name,
            "version": self.version,
            "classifier_type": (
                "drebin_style_heuristic"
            ),
            "risk_score": risk_score,
            "risk_level": risk_level,
            "matched_features": matched_features,
            "feature_names": feature_result.get(
                "feature_names",
                [],
            ),
            "feature_vector": feature_result.get(
                "feature_vector",
                [],
            ),
        }

    def _calculate_risk(
        self,
        features: dict[str, Any],
    ) -> float:
        score = 0.0

        for feature_name, weight in self.FEATURE_WEIGHTS.items():
            raw_value = features.get(feature_name, 0)

            if feature_name in self.COUNT_FEATURES:
                try:
                    value = max(
                        0.0,
                        float(raw_value),
                    )
                except (TypeError, ValueError):
                    value = 0.0

                value = min(value, 3.0)
            else:
                if isinstance(raw_value, bool):
                    value = (
                        1.0
                        if raw_value
                        else 0.0
                    )
                else:
                    try:
                        value = float(raw_value)
                    except (TypeError, ValueError):
                        value = 0.0

                value = 1.0 if value > 0 else 0.0

            score += value * weight

        return round(
            min(max(score, 0.0), 1.0),
            6,
        )

    @staticmethod
    def _risk_level(
        risk_score: float,
    ) -> str:
        if risk_score >= 0.70:
            return "HIGH"

        if risk_score >= 0.40:
            return "MEDIUM"

        return "LOW"
