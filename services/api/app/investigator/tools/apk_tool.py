"""APK structural, static, and heuristic risk intelligence tool."""

from __future__ import annotations

import time
from typing import Any
from uuid import UUID, uuid4

from app.contracts.evidence import EvidenceContract
from app.contracts.status import AnalysisStatus, EvidenceType, SeverityLevel
from app.investigator.tools.base import InvestigationTool, ToolResult
from app.providers.apk_analyzer import APKAnalyzer
from app.providers.apk_classifier import DrebinAPKClassifier
from app.providers.apk_feature_extractor import APKFeatureExtractor
from app.providers.apk_static_analyzer import APKStaticAnalyzer


class APKIntelligenceTool(InvestigationTool):
    """Perform deterministic, non-executing APK intelligence analysis."""

    def __init__(
        self,
        analyzer: APKAnalyzer | None = None,
        static_analyzer: APKStaticAnalyzer | None = None,
        feature_extractor: APKFeatureExtractor | None = None,
        classifier: DrebinAPKClassifier | None = None,
    ) -> None:
        self.analyzer = analyzer or APKAnalyzer()
        self.static_analyzer = (
            static_analyzer or APKStaticAnalyzer()
        )
        self.feature_extractor = (
            feature_extractor or APKFeatureExtractor()
        )
        self.classifier = classifier or DrebinAPKClassifier(
            analyzer=self.analyzer,
            static_analyzer=self.static_analyzer,
            feature_extractor=self.feature_extractor,
        )

    @property
    def name(self) -> str:
        return "apk_intelligence"

    @property
    def description(self) -> str:
        return (
            "Performs deterministic APK structural and static analysis "
            "including hashing, manifest, DEX, strings, URLs, IP "
            "addresses, Android API indicators, native libraries, "
            "obfuscation signals, and heuristic risk classification."
        )

    @property
    def version(self) -> str:
        return "1.2.0"

    async def execute(self, state: dict[str, Any]) -> ToolResult:
        start_time = time.perf_counter()

        investigation_id = self._get_uuid(
            state.get("investigation_id"),
            default=uuid4(),
        )
        input_id = self._get_optional_uuid(
            state.get("input_id")
        )

        apk_bytes = (
            state.get("apk_bytes")
            or state.get("media_bytes")
        )
        filename = state.get("filename")

        if not isinstance(apk_bytes, bytes) or not apk_bytes:
            duration_ms = self._duration_ms(start_time)

            evidence = EvidenceContract(
                investigation_id=investigation_id,
                input_id=input_id,
                type=EvidenceType.APK_ANALYSIS,
                category="apk_static_analysis",
                severity=SeverityLevel.INFORMATIONAL,
                confidence=0.0,
                description="No APK bytes were provided for analysis.",
                source_type="heuristic",
                source_name=self.name,
                source_version=self.version,
                status=AnalysisStatus.INSUFFICIENT_EVIDENCE,
                metadata={"is_skipped": True},
            )

            return ToolResult(
                tool_name=self.name,
                tool_version=self.version,
                status=AnalysisStatus.INSUFFICIENT_EVIDENCE,
                evidence=[evidence],
                output_data={},
                duration_ms=duration_ms,
            )

        try:
            structural_result = self.analyzer.analyze(
                apk_bytes=apk_bytes,
                filename=filename,
            )

            static_result = self.static_analyzer.analyze(
                apk_bytes
            )

            is_valid = bool(
                structural_result.get("is_valid")
            )

            if not is_valid:
                duration_ms = self._duration_ms(start_time)

                status = AnalysisStatus.FAILED
                severity = SeverityLevel.INFORMATIONAL
                confidence = 1.0

                description = (
                    "APK structural validation failed. "
                    + " ".join(
                        structural_result.get(
                            "warnings",
                            [],
                        )
                    )
                )

                combined_output = {
                    **structural_result,
                    "static_analysis": static_result,
                }

                evidence = EvidenceContract(
                    investigation_id=investigation_id,
                    input_id=input_id,
                    type=EvidenceType.APK_ANALYSIS,
                    category="apk_static_analysis",
                    severity=severity,
                    confidence=confidence,
                    description=description,
                    source_type="heuristic",
                    source_name=self.name,
                    source_version=self.version,
                    status=status,
                    raw_payload=combined_output,
                    metadata={
                        "sha256": structural_result.get(
                            "sha256"
                        ),
                        "size_bytes": structural_result.get(
                            "size_bytes"
                        ),
                        "classification_skipped": True,
                    },
                )

                return ToolResult(
                    tool_name=self.name,
                    tool_version=self.version,
                    status=status,
                    evidence=[evidence],
                    output_data=combined_output,
                    duration_ms=duration_ms,
                )

            feature_result = self.feature_extractor.extract(
                structural_result=structural_result,
                static_result=static_result,
            )

            classification = self.classifier.classify_features(
                feature_result
            )

            risk_score = classification["risk_score"]
            risk_level = classification["risk_level"]

            static_indicator_count = self._indicator_count(
                static_result
            )

            severity = self._severity_from_risk(
                risk_level=risk_level,
                static_indicator_count=static_indicator_count,
            )

            status = AnalysisStatus.SUCCESS
            confidence = 1.0

            description = (
                "APK structural, static, and heuristic "
                "classification analysis completed. "
                f"Risk score: {risk_score:.4f} "
                f"({risk_level}). Found "
                f"{static_result.get('string_count', 0)} "
                "string(s), "
                f"{len(static_result.get('urls', []))} "
                "URL(s), "
                f"{len(static_result.get('ip_addresses', []))} "
                "IP address(es), "
                f"{len(static_result.get('api_indicators', []))} "
                "API indicator(s), and "
                f"{len(static_result.get('obfuscation_indicators', []))} "
                "obfuscation indicator(s). "
                "The risk score is a deterministic heuristic "
                "signal, not a trained fraud probability."
            )

            combined_output = {
                **structural_result,
                "static_analysis": static_result,
                "feature_extraction": feature_result,
                "classification": classification,
            }

            evidence = EvidenceContract(
                investigation_id=investigation_id,
                input_id=input_id,
                type=EvidenceType.APK_ANALYSIS,
                category="apk_static_analysis",
                severity=severity,
                confidence=confidence,
                description=description,
                source_type="heuristic",
                source_name=self.name,
                source_version=self.version,
                status=status,
                raw_payload=combined_output,
                metadata={
                    "sha256": structural_result.get(
                        "sha256"
                    ),
                    "size_bytes": structural_result.get(
                        "size_bytes"
                    ),
                    "dex_count": structural_result.get(
                        "dex_count",
                        0,
                    ),
                    "native_library_count": structural_result.get(
                        "native_library_count",
                        0,
                    ),
                    "string_count": static_result.get(
                        "string_count",
                        0,
                    ),
                    "url_count": len(
                        static_result.get(
                            "urls",
                            [],
                        )
                    ),
                    "ip_count": len(
                        static_result.get(
                            "ip_addresses",
                            [],
                        )
                    ),
                    "api_indicator_count": len(
                        static_result.get(
                            "api_indicators",
                            [],
                        )
                    ),
                    "obfuscation_indicator_count": len(
                        static_result.get(
                            "obfuscation_indicators",
                            [],
                        )
                    ),
                    "classifier": self.classifier.provider_name,
                    "classifier_version": self.classifier.version,
                    "classifier_type": (
                        "drebin_style_heuristic"
                    ),
                    "risk_score": risk_score,
                    "risk_level": risk_level,
                    "matched_feature_count": len(
                        classification[
                            "matched_features"
                        ]
                    ),
                },
            )

            duration_ms = self._duration_ms(start_time)

            return ToolResult(
                tool_name=self.name,
                tool_version=self.version,
                status=status,
                evidence=[evidence],
                output_data=combined_output,
                duration_ms=duration_ms,
            )

        except Exception as exc:
            duration_ms = self._duration_ms(start_time)

            evidence = EvidenceContract(
                investigation_id=investigation_id,
                input_id=input_id,
                type=EvidenceType.APK_ANALYSIS,
                category="apk_static_analysis",
                severity=SeverityLevel.INFORMATIONAL,
                confidence=0.0,
                description=f"APK analysis failed: {exc}",
                source_type="heuristic",
                source_name=self.name,
                source_version=self.version,
                status=AnalysisStatus.FAILED,
                metadata={"error": str(exc)},
            )

            return ToolResult(
                tool_name=self.name,
                tool_version=self.version,
                status=AnalysisStatus.FAILED,
                evidence=[evidence],
                output_data={},
                error_message=str(exc),
                duration_ms=duration_ms,
            )

    @staticmethod
    def _indicator_count(
        static_result: dict[str, Any],
    ) -> int:
        return sum(
            len(static_result.get(key, []))
            for key in (
                "urls",
                "ip_addresses",
                "api_indicators",
                "obfuscation_indicators",
            )
        )

    @staticmethod
    def _severity_from_risk(
        *,
        risk_level: str,
        static_indicator_count: int,
    ) -> SeverityLevel:
        static_severity = SeverityLevel.LOW

        if static_indicator_count >= 4:
            static_severity = SeverityLevel.HIGH
        elif static_indicator_count >= 2:
            static_severity = SeverityLevel.MEDIUM

        classifier_severity = {
            "HIGH": SeverityLevel.HIGH,
            "MEDIUM": SeverityLevel.MEDIUM,
            "LOW": SeverityLevel.LOW,
        }.get(
            risk_level,
            SeverityLevel.INFORMATIONAL,
        )

        severity_rank = {
            SeverityLevel.INFORMATIONAL: 0,
            SeverityLevel.LOW: 1,
            SeverityLevel.MEDIUM: 2,
            SeverityLevel.HIGH: 3,
            SeverityLevel.CRITICAL: 4,
        }

        if (
            severity_rank[classifier_severity]
            > severity_rank[static_severity]
        ):
            return classifier_severity

        return static_severity

    @staticmethod
    def _get_uuid(
        value: Any,
        default: UUID,
    ) -> UUID:
        if isinstance(value, UUID):
            return value

        if value:
            return UUID(str(value))

        return default

    @staticmethod
    def _get_optional_uuid(
        value: Any,
    ) -> UUID | None:
        if value is None or value == "":
            return None

        if isinstance(value, UUID):
            return value

        return UUID(str(value))

    @staticmethod
    def _duration_ms(
        start_time: float,
    ) -> float:
        return round(
            (time.perf_counter() - start_time) * 1000,
            2,
        )
