"""APK structural intelligence investigation tool."""

from __future__ import annotations

import time
from typing import Any
from uuid import UUID, uuid4

from app.contracts.evidence import EvidenceContract
from app.contracts.status import AnalysisStatus, EvidenceType, SeverityLevel
from app.investigator.tools.base import InvestigationTool, ToolResult
from app.providers.apk_analyzer import APKAnalyzer


class APKIntelligenceTool(InvestigationTool):
    """Perform deterministic, non-executing APK structural analysis."""

    def __init__(self, analyzer: APKAnalyzer | None = None) -> None:
        self.analyzer = analyzer or APKAnalyzer()

    @property
    def name(self) -> str:
        return "apk_intelligence"

    @property
    def description(self) -> str:
        return (
            "Performs deterministic APK structural analysis including "
            "hashing, manifest, DEX, native-library, and archive checks."
        )

    @property
    def version(self) -> str:
        return "1.0.0"

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
                category="apk_structural_analysis",
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
            result = self.analyzer.analyze(
                apk_bytes=apk_bytes,
                filename=filename,
            )
            duration_ms = self._duration_ms(start_time)

            is_valid = bool(result.get("is_valid"))
            suspicious_entries = result.get("suspicious_entries", [])

            if is_valid:
                severity = (
                    SeverityLevel.MEDIUM
                    if suspicious_entries
                    else SeverityLevel.LOW
                )
                status = AnalysisStatus.SUCCESS
                confidence = 1.0
                description = (
                    "APK structural analysis completed successfully. "
                    f"Detected {result.get('dex_count', 0)} DEX file(s), "
                    f"{result.get('native_library_count', 0)} native "
                    "library file(s), and "
                    f"{len(suspicious_entries)} suspicious archive "
                    "entry/entries."
                )
            else:
                severity = SeverityLevel.INFORMATIONAL
                status = AnalysisStatus.FAILED
                confidence = 1.0
                description = (
                    "APK structural validation failed. "
                    + " ".join(result.get("warnings", []))
                )

            evidence = EvidenceContract(
                investigation_id=investigation_id,
                input_id=input_id,
                type=EvidenceType.APK_ANALYSIS,
                category="apk_structural_analysis",
                severity=severity,
                confidence=confidence,
                description=description,
                source_type="heuristic",
                source_name=self.name,
                source_version=self.version,
                status=status,
                raw_payload=result,
                metadata={
                    "sha256": result.get("sha256"),
                    "size_bytes": result.get("size_bytes"),
                    "dex_count": result.get("dex_count", 0),
                    "native_library_count": result.get(
                        "native_library_count",
                        0,
                    ),
                    "suspicious_entry_count": len(
                        suspicious_entries
                    ),
                    "has_android_manifest": result.get(
                        "has_android_manifest",
                        False,
                    ),
                },
            )

            return ToolResult(
                tool_name=self.name,
                tool_version=self.version,
                status=status,
                evidence=[evidence],
                output_data=result,
                duration_ms=duration_ms,
            )

        except Exception as exc:
            duration_ms = self._duration_ms(start_time)

            evidence = EvidenceContract(
                investigation_id=investigation_id,
                input_id=input_id,
                type=EvidenceType.APK_ANALYSIS,
                category="apk_structural_analysis",
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
        return round((time.perf_counter() - start_time) * 1000, 2)
