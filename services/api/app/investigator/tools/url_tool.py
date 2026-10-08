"""VERA deterministic URL intelligence investigation tool."""

from __future__ import annotations

from time import perf_counter
from typing import Any

from app.contracts.evidence import EvidenceContract
from app.contracts.status import AnalysisStatus, EvidenceType, SeverityLevel
from app.investigator.tools.base import InvestigationTool, ToolResult
from app.providers.url_analyzer import URLAnalyzer


class URLIntelligenceTool(InvestigationTool):
    """Analyze URLs using deterministic, network-free intelligence."""

    name = "url_intelligence"
    description = (
        "Performs deterministic URL structure analysis without network access."
    )
    version = "1.0.0"

    def __init__(self, analyzer: URLAnalyzer | None = None) -> None:
        self._analyzer = analyzer or URLAnalyzer()

    async def execute(self, state: dict[str, Any]) -> ToolResult:
        """Analyze a URL from the current investigation state."""

        started_at = perf_counter()

        investigation_id = state.get("investigation_id")
        url = state.get("raw_input_text") or state.get("normalized_input")

        if not isinstance(url, str) or not url.strip():
            duration_ms = (perf_counter() - started_at) * 1000

            return ToolResult(
                tool_name=self.name,
                tool_version=self.version,
                status=AnalysisStatus.FAILED,
                evidence=[],
                output_data={},
                error_message="URL input is missing or invalid.",
                duration_ms=duration_ms,
            )

        if investigation_id is None:
            duration_ms = (perf_counter() - started_at) * 1000

            return ToolResult(
                tool_name=self.name,
                tool_version=self.version,
                status=AnalysisStatus.FAILED,
                evidence=[],
                output_data={},
                error_message="Investigation ID is missing.",
                duration_ms=duration_ms,
            )

        try:
            result = self._analyzer.analyze(url)

            duration_ms = (perf_counter() - started_at) * 1000

            if not result.is_valid:
                return ToolResult(
                    tool_name=self.name,
                    tool_version=self.version,
                    status=AnalysisStatus.FAILED,
                    evidence=[],
                    output_data=result.model_dump(),
                    error_message=(
                        result.warnings[0]
                        if result.warnings
                        else "URL analysis failed."
                    ),
                    duration_ms=duration_ms,
                )

            severity = self._derive_severity(result.indicators)

            evidence = EvidenceContract(
                investigation_id=investigation_id,
                type=EvidenceType.URL_ANALYSIS,
                category="deterministic_url_analysis",
                severity=severity,
                confidence=1.0,
                description=self._build_description(result),
                source_type="heuristic",
                source_name=self.name,
                source_version=self.version,
                status=AnalysisStatus.SUCCESS,
                raw_payload=result.model_dump(),
                metadata={
                    "normalized_url": result.normalized_url,
                    "indicators": result.indicators,
                    "suspicious_keyword_hits": result.suspicious_keyword_hits,
                },
            )

            return ToolResult(
                tool_name=self.name,
                tool_version=self.version,
                status=AnalysisStatus.SUCCESS,
                evidence=[evidence],
                output_data=result.model_dump(),
                duration_ms=duration_ms,
            )

        except Exception as exc:
            duration_ms = (perf_counter() - started_at) * 1000

            return ToolResult(
                tool_name=self.name,
                tool_version=self.version,
                status=AnalysisStatus.FAILED,
                evidence=[],
                output_data={},
                error_message=f"URL analysis failed: {exc}",
                duration_ms=duration_ms,
            )

    @staticmethod
    def _derive_severity(indicators: list[str]) -> SeverityLevel:
        """Map deterministic URL indicators to an evidence severity."""

        high_risk_indicators = {
            "embedded_credentials",
            "ip_address_host",
            "punycode_hostname",
        }

        medium_risk_indicators = {
            "deep_subdomain_structure",
            "explicit_nonstandard_port",
            "very_long_url",
            "high_special_character_count",
            "suspicious_keywords",
        }

        if any(indicator in high_risk_indicators for indicator in indicators):
            return SeverityLevel.HIGH

        if any(indicator in medium_risk_indicators for indicator in indicators):
            return SeverityLevel.MEDIUM

        if "insecure_http" in indicators:
            return SeverityLevel.LOW

        return SeverityLevel.INFORMATIONAL

    @staticmethod
    def _build_description(result: Any) -> str:
        """Build a deterministic human-readable evidence description."""

        if not result.indicators:
            return "No suspicious URL structure indicators were detected."

        indicators = ", ".join(result.indicators)

        return (
            "Deterministic URL analysis detected the following indicators: "
            f"{indicators}."
        )