"""VERA URL intelligence investigation tool."""

from __future__ import annotations

from time import perf_counter
from typing import Any
from urllib.parse import urlsplit

from app.contracts.evidence import EvidenceContract
from app.contracts.status import AnalysisStatus, EvidenceType, SeverityLevel
from app.investigator.tools.base import InvestigationTool, ToolResult
from app.providers.dns_intelligence import DNSIntelligenceProvider
from app.providers.url_analyzer import URLAnalyzer


class URLIntelligenceTool(InvestigationTool):
    """Analyze URLs using deterministic and DNS intelligence."""

    name = "url_intelligence"
    description = (
        "Performs deterministic URL structure analysis and DNS intelligence."
    )
    version = "1.1.0"

    def __init__(
        self,
        analyzer: URLAnalyzer | None = None,
        dns_provider: DNSIntelligenceProvider | None = None,
    ) -> None:
        self._analyzer = analyzer or URLAnalyzer()
        self._dns_provider = dns_provider or DNSIntelligenceProvider()

    async def execute(self, state: dict[str, Any]) -> ToolResult:
        """Analyze a URL from the current investigation state."""

        started_at = perf_counter()

        investigation_id = state.get("investigation_id")
        url = state.get("raw_input_text") or state.get("normalized_input")

        if not isinstance(url, str) or not url.strip():
            return self._failed_result(
                started_at,
                "URL input is missing or invalid.",
            )

        if investigation_id is None:
            return self._failed_result(
                started_at,
                "Investigation ID is missing.",
            )

        try:
            result = self._analyzer.analyze(url)

            if not result.is_valid:
                duration_ms = (perf_counter() - started_at) * 1000

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

            evidence: list[EvidenceContract] = []

            deterministic_evidence = self._build_url_evidence(
                investigation_id=investigation_id,
                result=result,
            )
            evidence.append(deterministic_evidence)

            dns_result = await self._dns_provider.resolve_domain(
                investigation_id=investigation_id,
                hostname=result.hostname,
            )

            dns_evidence = self._build_dns_evidence(
                investigation_id=investigation_id,
                dns_result=dns_result,
            )
            evidence.append(dns_evidence)

            duration_ms = (perf_counter() - started_at) * 1000

            output_data = {
                "url_analysis": result.model_dump(),
                "dns_analysis": dns_result,
            }

            return ToolResult(
                tool_name=self.name,
                tool_version=self.version,
                status=AnalysisStatus.SUCCESS,
                evidence=evidence,
                output_data=output_data,
                duration_ms=duration_ms,
            )

        except Exception as exc:
            return self._failed_result(
                started_at,
                f"URL intelligence failed: {exc}",
            )

    def _build_url_evidence(
        self,
        investigation_id: Any,
        result: Any,
    ) -> EvidenceContract:
        """Build deterministic URL evidence."""

        severity = self._derive_severity(result.indicators)

        return EvidenceContract(
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

    @staticmethod
    def _build_dns_evidence(
        investigation_id: Any,
        dns_result: dict[str, Any],
    ) -> EvidenceContract:
        """Build evidence from the DNS provider result."""

        status_value = dns_result.get(
            "status",
            AnalysisStatus.FAILED.value,
        )

        try:
            status = AnalysisStatus(status_value)
        except ValueError:
            status = AnalysisStatus.FAILED

        if status == AnalysisStatus.SUCCESS:
            addresses = dns_result.get("addresses", [])

            description = (
                "DNS resolution succeeded for "
                f"{dns_result.get('hostname')}: "
                f"{', '.join(addresses)}."
            )

            severity = SeverityLevel.INFORMATIONAL

        elif status == AnalysisStatus.UNAVAILABLE:
            description = (
                "DNS intelligence was unavailable; no DNS conclusion "
                "was made."
            )
            severity = SeverityLevel.INFORMATIONAL

        else:
            description = (
                "DNS resolution failed for "
                f"{dns_result.get('hostname')}; "
                "no DNS conclusion was made."
            )
            severity = SeverityLevel.INFORMATIONAL

        return EvidenceContract(
            investigation_id=investigation_id,
            type=EvidenceType.FORENSIC_ARTIFACT,
            category="dns_intelligence",
            severity=severity,
            confidence=1.0 if status == AnalysisStatus.SUCCESS else 0.0,
            description=description,
            source_type="network",
            source_name="dns_intelligence",
            source_version="1.0.0",
            status=status,
            raw_payload=dns_result,
            metadata={
                "hostname": dns_result.get("hostname"),
                "addresses": dns_result.get("addresses", []),
                "address_count": dns_result.get("address_count", 0),
            },
        )

    @staticmethod
    def _failed_result(
        started_at: float,
        error_message: str,
    ) -> ToolResult:
        """Build a failed tool result."""

        duration_ms = (perf_counter() - started_at) * 1000

        return ToolResult(
            tool_name=URLIntelligenceTool.name,
            tool_version=URLIntelligenceTool.version,
            status=AnalysisStatus.FAILED,
            evidence=[],
            output_data={},
            error_message=error_message,
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