"""Investigator tool for deterministic APK intelligence."""

from __future__ import annotations

from typing import Any

from app.contracts.evidence import EvidenceContract
from app.contracts.status import AnalysisStatus, EvidenceType, SeverityLevel
from app.investigator.tools.base import InvestigationTool, ToolResult
from app.providers.apk_analyzer import APKAnalyzerProvider
from app.providers.apk_static_features import APKStaticFeatureExtractor


class APKIntelligenceTool(InvestigationTool):
    """Analyze APK foundation, manifest, and signing-certificate metadata."""

    name = "apk_intelligence"
    description = (
        "Performs deterministic APK validation, manifest, component, "
        "SDK, and signing-certificate analysis."
    )
    version = "1.0.0"

    def __init__(
        self,
        analyzer: APKAnalyzerProvider | None = None,
        feature_extractor: APKStaticFeatureExtractor | None = None,
    ) -> None:
        self.analyzer = analyzer or APKAnalyzerProvider()
        self.feature_extractor = (
            feature_extractor or APKStaticFeatureExtractor()
        )

    async def execute(self, state: dict[str, Any]) -> ToolResult:
        """Execute deterministic APK intelligence."""

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
            foundation = await self.analyzer.analyze(apk_path)

            if foundation.get("status") != AnalysisStatus.SUCCESS.value:
                return ToolResult(
                    tool_name=self.name,
                    tool_version=self.version,
                    status=AnalysisStatus(foundation["status"]),
                    evidence=[],
                    output_data={"apk_analysis": foundation},
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

            certificates = await self.analyzer.analyze_certificates(apk_path)

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

            static_features = {
                "status": AnalysisStatus.INSUFFICIENT_EVIDENCE.value,
                "feature_vector": {},
                "feature_count": 0,
            }

            if (
                manifest.get("status") == AnalysisStatus.SUCCESS.value
                and certificates.get("status") == AnalysisStatus.SUCCESS.value
            ):
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
                "member_count": result.get("archive", {}).get("member_count"),
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
                "activity_count": len(components.get("activities", [])),
                "service_count": len(components.get("services", [])),
                "receiver_count": len(components.get("receivers", [])),
                "provider_count": len(components.get("providers", [])),
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
                "signature_schemes": result.get("signature_schemes", []),
                "certificate_count": result.get("certificate_count", 0),
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

        return EvidenceContract(
            investigation_id=investigation_id,
            type=EvidenceType.FORENSIC_ARTIFACT,
            category="apk_static_features",
            severity=SeverityLevel.INFORMATIONAL,
            confidence=1.0 if result.get("status") == AnalysisStatus.SUCCESS.value else 0.0,
            description=(
                "Deterministic static APK feature vector was extracted "
                f"with {len(feature_vector)} feature(s)."
            ),
            source_type="static_analysis",
            source_name="apk_static_feature_extractor",
            source_version="1.0.0",
            status=AnalysisStatus(
                result.get(
                    "status",
                    AnalysisStatus.INSUFFICIENT_EVIDENCE.value,
                )
            ),
            raw_payload=result,
            metadata={
                "feature_count": len(feature_vector),
                "feature_names": sorted(feature_vector.keys()),
            },
        )

    @staticmethod
    def _build_failed_evidence(
        investigation_id: Any,
        category: str,
        description: str,
        result: dict[str, Any],
    ) -> EvidenceContract:
        status = AnalysisStatus(
            result.get("status", AnalysisStatus.FAILED.value)
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
            metadata={"error": result.get("error")},
        )
