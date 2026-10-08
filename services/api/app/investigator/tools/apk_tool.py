"""APK structural and static intelligence investigation tool."""

from __future__ import annotations

import time
from typing import Any
from uuid import UUID, uuid4

from app.contracts.evidence import EvidenceContract
from app.contracts.status import AnalysisStatus, EvidenceType, SeverityLevel
from app.investigator.tools.base import InvestigationTool, ToolResult
from app.providers.apk_analyzer import APKAnalyzer
from app.providers.apk_static_analyzer import APKStaticAnalyzer


class APKIntelligenceTool(InvestigationTool):
    """Perform deterministic, non-executing APK intelligence analysis."""

    def __init__(
        self,
        analyzer: APKAnalyzer | None = None,
        static_analyzer: APKStaticAnalyzer | None = None,
    ) -> None:
        self.analyzer = analyzer or APKAnalyzer()
        self.static_analyzer = static_analyzer or APKStaticAnalyzer()

    @property
    def name(self) -> str:
        return "apk_intelligence"

    @property
    def description(self) -> str:
        return (
            "Performs deterministic APK structural and static analysis "
            "including hashing, manifest, DEX, strings, URLs, IP addresses, "
            "Android API indicators, native libraries, and obfuscation signals."
        )

    @property
    def version(self) -> str:
        return "1.1.0"

    async def execute(self, state: dict[str, Any]) -> ToolResult:
        start_time = time.perf_counter()

        investigation_id = self._get_uuid(
            state.get("investigation_id"),
            default=uuid4(),
        )
        input_id = self._get_optional_uuid(state.get("input_id"))

        apk_bytes = state.get("apk_bytes") or state.get("media_bytes")
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

            static_result = self.static_analyzer.analyze(apk_bytes)

            duration_ms = self._duration_ms(start_time)

            is_valid = bool(structural_result.get("is_valid"))

            if not is_valid:
                status = AnalysisStatus.FAILED
                severity = SeverityLevel.INFORMATIONAL
                confidence = 1.0
                description = (
                    "APK structural validation failed. "
                    + " ".join(
                        structural_result.get("warnings", [])
                    )
                )
            else:
                indicator_count = self._indicator_count(
                    static_result
                )

                if indicator_count >= 4:
                    severity = SeverityLevel.HIGH
                elif indicator_count >= 2:
                    severity = SeverityLevel.MEDIUM
                else:
                    severity = SeverityLevel.LOW

                status = AnalysisStatus.SUCCESS
                confidence = 1.0
                description = (
                    "APK structural and static analysis completed. "
                    f"Found {static_result.get('string_count', 0)} "
                    f"string(s), {len(static_result.get('urls', []))} "
                    f"URL(s), {len(static_result.get('ip_addresses', []))} "
                    f"IP address(es), "
                    f"{len(static_result.get('api_indicators', []))} "
                    "API indicator(s), and "
                    f"{len(static_result.get('obfuscation_indicators', []))} "
                    "obfuscation indicator(s)."
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
                    "sha256": structural_result.get("sha256"),
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
                        static_result.get("urls", [])
                    ),
                    "ip_count": len(
                        static_result.get("ip_addresses", [])
                    ),
                    "api_indicator_count": len(
                        static_result.get("api_indicators", [])
                    ),
                    "obfuscation_indicator_count": len(
                        static_result.get(
                            "obfuscation_indicators",
                            [],
                        )
                    ),
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
    def _indicator_count(static_result: dict[str, Any]) -> int:
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
    def _get_uuid(value: Any, default: UUID) -> UUID:
        if isinstance(value, UUID):
            return value

        if value:
            return UUID(str(value))

        return default

    @staticmethod
    def _get_optional_uuid(value: Any) -> UUID | None:
        if value is None or value == "":
            return None

        if isinstance(value, UUID):
            return value

        return UUID(str(value))

    @staticmethod
    def _duration_ms(start_time: float) -> float:
        return round(
            (time.perf_counter() - start_time) * 1000,
            2,
        )
