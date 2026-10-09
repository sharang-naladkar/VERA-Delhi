"""Investigator tool for deterministic APK intelligence."""

from __future__ import annotations

from typing import Any

from app.contracts.evidence import EvidenceContract
from app.contracts.status import AnalysisStatus, EvidenceType, SeverityLevel
from app.investigator.tools.base import InvestigationTool, ToolResult
from app.providers.apk_analyzer import APKAnalyzerProvider
from app.providers.apk_classifier import APKClassifier
from app.providers.apk_static_features import APKStaticFeatureExtractor


class APKIntelligenceTool(InvestigationTool):
    """Analyze APK files and optionally classify extracted static features."""

    name = "apk_intelligence"
    description = (
        "Performs deterministic APK validation, manifest, component, "
        "SDK, signing-certificate, static-feature, and optional "
        "machine-learning classification analysis."
    )
    version = "1.1.0"

    def __init__(
        self,
        analyzer: APKAnalyzerProvider | None = None,
        feature_extractor: APKStaticFeatureExtractor | None = None,
        classifier: APKClassifier | None = None,
    ) -> None:
        self.analyzer = analyzer or APKAnalyzerProvider()
        self.feature_extractor = (
            feature_extractor or APKStaticFeatureExtractor()
        )
        self.classifier = classifier or APKClassifier()

    async def execute(self, state: dict[str, Any]) -> ToolResult:
        """Execute APK intelligence with fail-safe classification."""

        investigation_id = state.get("investigation_id")

        apk_path = (
            state.get("apk_path")
            or state.get("file_path")
            or state.get("input_file_path")
        )

        if not investigation_id:
            return ToolResult(
                tool_name=self.name,
                tool_version=self.version,
                status=AnalysisStatus.FAILED,
                evidence=[],
                error_message="Investigation ID is missing.",
            )

        if not apk_path:
            return ToolResult(
                tool_name=self.name,
                tool_version=self.version,
                status=AnalysisStatus.FAILED,
                evidence=[],
                error_message="APK input is missing.",
            )

        try:
            # Stage 1: Validate the APK and extract foundation metadata.
            foundation = await self.analyzer.analyze(apk_path)

            if foundation.get("status") != AnalysisStatus.SUCCESS.value:
                return ToolResult(
                    tool_name=self.name,
                    tool_version=self.version,
                    status=self._parse_status(
                        foundation.get("status"),
                        AnalysisStatus.FAILED,
                    ),
                    evidence=[],
                    output_data={
                        "apk_analysis": foundation,
                    },
                    error_message=foundation.get(
                        "error",
                        "APK foundation analysis failed.",
                    ),
                )

            evidence: list[EvidenceContract] = []

            evidence.append(
                self._build_foundation_evidence(
                    investigation_id,
                    foundation,
                )
            )

            # Stage 2: Analyze the Android manifest.
            manifest = await self.analyzer.analyze_manifest(apk_path)

            if manifest.get("status") == AnalysisStatus.SUCCESS.value:
                evidence.append(
                    self._build_manifest_evidence(
                        investigation_id,
                        manifest,
                    )
                )
            else:
                evidence.append(
                    self._build_failed_evidence(
                        investigation_id,
                        "apk_manifest_analysis",
                        (
                            "APK manifest analysis did not produce "
                            "verified manifest metadata."
                        ),
                        manifest,
                    )
                )

            # Stage 3: Analyze signing certificates.
            certificates = await self.analyzer.analyze_certificates(
                apk_path
            )

            if certificates.get("status") == AnalysisStatus.SUCCESS.value:
                evidence.append(
                    self._build_certificate_evidence(
                        investigation_id,
                        certificates,
                    )
                )
            else:
                evidence.append(
                    self._build_failed_evidence(
                        investigation_id,
                        "apk_certificate_analysis",
                        (
                            "APK certificate analysis did not produce "
                            "verified signing-certificate metadata."
                        ),
                        certificates,
                    )
                )

            # Stage 4: Extract deterministic static features.
            static_features = {
                "status": AnalysisStatus.INSUFFICIENT_EVIDENCE.value,
                "feature_vector": {},
                "feature_count": 0,
            }

            manifest_available = (
                manifest.get("status") == AnalysisStatus.SUCCESS.value
            )
            certificates_available = (
                certificates.get("status") == AnalysisStatus.SUCCESS.value
            )

            if manifest_available and certificates_available:
                static_features = self.feature_extractor.extract(
                    foundation,
                    manifest,
                    certificates,
                )

                evidence.append(
                    self._build_static_feature_evidence(
                        investigation_id,
                        static_features,
                    )
                )

            # Stage 5: Classify the extracted feature vector.
            #
            # Classification is optional. Missing models, unavailable
            # classifiers, or classification errors must not invalidate
            # successful deterministic APK analysis.
            if (
                static_features.get("status")
                == AnalysisStatus.SUCCESS.value
            ):
                try:
                    apk_classification = await self.classifier.classify(
                        static_features["feature_vector"]
                    )

                    if not isinstance(apk_classification, dict):
                        apk_classification = {
                            "status": AnalysisStatus.FAILED.value,
                            "prediction": None,
                            "model_score": None,
                            "model_version": None,
                            "feature_count": 0,
                            "error": (
                                "Classifier returned an invalid response."
                            ),
                        }

                except Exception as exc:
                    apk_classification = {
                        "status": AnalysisStatus.FAILED.value,
                        "prediction": None,
                        "model_score": None,
                        "model_version": None,
                        "feature_count": 0,
                        "error": (
                            "APK classification failed: "
                            f"{type(exc).__name__}: {exc}"
                        ),
                    }
            else:
                apk_classification = {
                    "status": AnalysisStatus.INSUFFICIENT_EVIDENCE.value,
                    "prediction": None,
                    "model_score": None,
                    "model_version": None,
                    "feature_count": 0,
                    "error": (
                        "Classification skipped because verified "
                        "static APK features were unavailable."
                    ),
                }

            # Stage 6: Record the classifier's result as separate evidence.
            evidence.append(
                self._build_classifier_evidence(
                    investigation_id,
                    apk_classification,
                )
            )

            # A classifier failure does not override successful
            # deterministic APK analysis.
            return ToolResult(
                tool_name=self.name,
                tool_version=self.version,
                status=AnalysisStatus.SUCCESS,
                evidence=evidence,
                output_data={
                    "apk_analysis": foundation,
                    "manifest_analysis": manifest,
                    "certificate_analysis": certificates,
                    "static_features": static_features,
                    "apk_classification": apk_classification,
                },
            )

        except Exception as exc:
            return ToolResult(
                tool_name=self.name,
                tool_version=self.version,
                status=AnalysisStatus.FAILED,
                evidence=[],
                error_message=f"APK intelligence failed: {exc}",
            )

    @staticmethod
    def _parse_status(
        value: Any,
        fallback: AnalysisStatus = AnalysisStatus.FAILED,
    ) -> AnalysisStatus:
        """Parse a status safely without inventing a successful result."""

        try:
            return AnalysisStatus(value)
        except (ValueError, TypeError):
            return fallback

    @staticmethod
    def _build_foundation_evidence(
        investigation_id: Any,
        result: dict[str, Any],
    ) -> EvidenceContract:
        return EvidenceContract(
            investigation_id=investigation_id,
            type=EvidenceType.FORENSIC_ARTIFACT,
            category="apk_foundation",
            severity=SeverityLevel.INFORMATIONAL,
            confidence=1.0,
            description=(
                "APK validation completed and deterministic file metadata "
                "was extracted."
            ),
            source_type="static_analysis",
            source_name="apk_analyzer",
            source_version="1.0.0",
            status=AnalysisStatus.SUCCESS,
            raw_payload=result,
            metadata={
                "sha256": result.get("sha256"),
                "file_size_bytes": result.get("file_size_bytes"),
                "member_count": result.get("archive", {}).get(
                    "member_count"
                ),
                "classes_dex_count": result.get("archive", {}).get(
                    "classes_dex_count"
                ),
            },
        )

    @staticmethod
    def _build_manifest_evidence(
        investigation_id: Any,
        result: dict[str, Any],
    ) -> EvidenceContract:
        permissions = result.get("permissions", [])
        components = result.get("components", {})

        return EvidenceContract(
            investigation_id=investigation_id,
            type=EvidenceType.FORENSIC_ARTIFACT,
            category="apk_manifest_analysis",
            severity=SeverityLevel.INFORMATIONAL,
            confidence=1.0,
            description=(
                "Android manifest metadata was parsed successfully, "
                f"including {len(permissions)} requested permission(s)."
            ),
            source_type="static_analysis",
            source_name="androguard",
            source_version="4.1.4",
            status=AnalysisStatus.SUCCESS,
            raw_payload=result,
            metadata={
                "package_name": result.get("package_name"),
                "permission_count": len(permissions),
                "activity_count": len(
                    components.get("activities", [])
                ),
                "service_count": len(
                    components.get("services", [])
                ),
                "receiver_count": len(
                    components.get("receivers", [])
                ),
                "provider_count": len(
                    components.get("providers", [])
                ),
                "min_sdk": result.get("sdk", {}).get("min"),
                "target_sdk": result.get("sdk", {}).get("target"),
            },
        )

    @staticmethod
    def _build_certificate_evidence(
        investigation_id: Any,
        result: dict[str, Any],
    ) -> EvidenceContract:
        return EvidenceContract(
            investigation_id=investigation_id,
            type=EvidenceType.FORENSIC_ARTIFACT,
            category="apk_certificate_analysis",
            severity=SeverityLevel.INFORMATIONAL,
            confidence=1.0,
            description=(
                "APK signing certificate metadata was extracted successfully."
            ),
            source_type="static_analysis",
            source_name="androguard",
            source_version="4.1.4",
            status=AnalysisStatus.SUCCESS,
            raw_payload=result,
            metadata={
                "signature_schemes": result.get(
                    "signature_schemes", []
                ),
                "certificate_count": result.get(
                    "certificate_count", 0
                ),
                "sha256_fingerprints": [
                    certificate.get("sha256_fingerprint")
                    for certificate in result.get("certificates", [])
                    if certificate.get("sha256_fingerprint")
                ],
            },
        )

    @staticmethod
    def _build_static_feature_evidence(
        investigation_id: Any,
        result: dict[str, Any],
    ) -> EvidenceContract:
        feature_vector = result.get("feature_vector", {})

        status = APKIntelligenceTool._parse_status(
            result.get("status"),
            AnalysisStatus.INSUFFICIENT_EVIDENCE,
        )

        return EvidenceContract(
            investigation_id=investigation_id,
            type=EvidenceType.FORENSIC_ARTIFACT,
            category="apk_static_features",
            severity=SeverityLevel.INFORMATIONAL,
            confidence=1.0 if status == AnalysisStatus.SUCCESS else 0.0,
            description=(
                "Deterministic static APK feature vector was extracted "
                f"with {len(feature_vector)} feature(s)."
            ),
            source_type="static_analysis",
            source_name="apk_static_feature_extractor",
            source_version="1.0.0",
            status=status,
            raw_payload=result,
            metadata={
                "feature_count": len(feature_vector),
                "feature_names": sorted(feature_vector.keys()),
            },
        )

    @staticmethod
    def _build_classifier_evidence(
        investigation_id: Any,
        result: dict[str, Any],
    ) -> EvidenceContract:
        status = APKIntelligenceTool._parse_status(
            result.get("status"),
            AnalysisStatus.FAILED,
        )

        successful = status == AnalysisStatus.SUCCESS

        return EvidenceContract(
            investigation_id=investigation_id,
            type=EvidenceType.FORENSIC_ARTIFACT,
            category="apk_ml_classification",
            severity=SeverityLevel.INFORMATIONAL,
            confidence=1.0 if successful else 0.0,
            description=(
                (
                    "Optional APK model classification output was produced. "
                    "This is an auxiliary model result, not a final "
                    "fraud determination."
                )
                if successful
                else (
                    "APK model classification did not produce a usable "
                    "prediction. This does not imply that the APK is safe."
                )
            ),
            source_type="static_analysis",
            source_name="apk_xgboost_classifier",
            source_version=str(
                result.get("model_version") or "1.0.0"
            ),
            status=status,
            raw_payload=result,
            metadata={
                "prediction": result.get("prediction"),
                "model_score": result.get("model_score"),
                "feature_count": result.get("feature_count", 0),
            },
        )

    @staticmethod
    def _build_failed_evidence(
        investigation_id: Any,
        category: str,
        description: str,
        result: dict[str, Any],
    ) -> EvidenceContract:
        status = APKIntelligenceTool._parse_status(
            result.get("status"),
            AnalysisStatus.FAILED,
        )

        return EvidenceContract(
            investigation_id=investigation_id,
            type=EvidenceType.FORENSIC_ARTIFACT,
            category=category,
            severity=SeverityLevel.INFORMATIONAL,
            confidence=0.0,
            description=description,
            source_type="static_analysis",
            source_name="apk_analyzer",
            source_version="1.0.0",
            status=status,
            raw_payload=result,
            metadata={
                "error": result.get("error"),
            },
        )