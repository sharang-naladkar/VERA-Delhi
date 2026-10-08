"""Investigator tool for deterministic URL intelligence."""

from __future__ import annotations

from typing import Any

from app.contracts.evidence import EvidenceContract
from app.contracts.status import AnalysisStatus, EvidenceType, SeverityLevel
from app.investigator.tools.base import InvestigationTool, ToolResult
from app.providers.dns_intelligence import DNSIntelligenceProvider
from app.providers.http_intelligence import HTTPIntelligenceProvider
from app.providers.tls_intelligence import TLSIntelligenceProvider
from app.providers.url_analyzer import URLAnalyzer


class URLIntelligenceTool(InvestigationTool):
    """Analyze URL structure and enrich it with DNS, TLS, and HTTP evidence."""

    name = "url_intelligence"
    description = (
        "Performs deterministic URL analysis with DNS, TLS, "
        "and HTTP intelligence."
    )
    version = "1.3.0"

    def __init__(
        self,
        analyzer: URLAnalyzer | None = None,
        dns_provider: DNSIntelligenceProvider | None = None,
        tls_provider: TLSIntelligenceProvider | None = None,
        http_provider: HTTPIntelligenceProvider | None = None,
    ) -> None:
        self.analyzer = analyzer or URLAnalyzer()
        self.dns_provider = dns_provider or DNSIntelligenceProvider()
        self.tls_provider = tls_provider or TLSIntelligenceProvider()
        self.http_provider = http_provider or HTTPIntelligenceProvider()

    async def execute(self, state: dict[str, Any]) -> ToolResult:
        """Execute URL, DNS, TLS, and HTTP intelligence."""

        investigation_id = state.get("investigation_id")
        url = state.get("raw_input_text") or state.get("normalized_input")

        if not investigation_id:
            return ToolResult(
                tool_name=self.name,
                tool_version=self.version,
                status=AnalysisStatus.FAILED,
                evidence=[],
                error_message="Investigation ID is missing.",
            )

        if not url:
            return ToolResult(
                tool_name=self.name,
                tool_version=self.version,
                status=AnalysisStatus.FAILED,
                evidence=[],
                error_message="URL input is missing.",
            )

        try:
            url_result = self.analyzer.analyze(url)

            if not url_result.is_valid:
                return ToolResult(
                    tool_name=self.name,
                    tool_version=self.version,
                    status=AnalysisStatus.FAILED,
                    evidence=[],
                    output_data=url_result.model_dump(),
                    error_message=(
                        url_result.warnings[0]
                        if url_result.warnings
                        else "URL analysis failed."
                    ),
                )

            evidence: list[EvidenceContract] = []

            url_evidence = self._build_url_evidence(
                investigation_id,
                url_result,
            )
            evidence.append(url_evidence)

            dns_result = await self.dns_provider.resolve_domain(
                investigation_id=investigation_id,
                hostname=url_result.hostname,
            )

            dns_evidence = self._build_dns_evidence(
                investigation_id,
                dns_result,
            )
            evidence.append(dns_evidence)

            tls_result: dict[str, Any] | None = None

            if url_result.scheme == "https":
                tls_result = await self.tls_provider.inspect_certificate(
                    investigation_id=investigation_id,
                    hostname=url_result.hostname,
                    port=url_result.port or 443,
                )

                tls_evidence = self._build_tls_evidence(
                    investigation_id,
                    tls_result,
                )
                evidence.append(tls_evidence)

            http_result = await self.http_provider.inspect_url(
                investigation_id=investigation_id,
                url=url_result.normalized_url,
            )

            http_evidence = self._build_http_evidence(
                investigation_id,
                http_result,
            )
            evidence.append(http_evidence)

            output_data: dict[str, Any] = {
                "url_analysis": url_result.model_dump(),
                "dns_analysis": dns_result,
                "http_analysis": http_result,
            }

            if tls_result is not None:
                output_data["tls_analysis"] = tls_result

            return ToolResult(
                tool_name=self.name,
                tool_version=self.version,
                status=AnalysisStatus.SUCCESS,
                evidence=evidence,
                output_data=output_data,
            )

        except Exception as exc:
            return ToolResult(
                tool_name=self.name,
                tool_version=self.version,
                status=AnalysisStatus.FAILED,
                evidence=[],
                error_message=f"URL intelligence failed: {exc}",
            )

    def _build_url_evidence(
        self,
        investigation_id: Any,
        result: Any,
    ) -> EvidenceContract:
        """Build deterministic URL evidence."""

        return EvidenceContract(
            investigation_id=investigation_id,
            type=EvidenceType.URL_ANALYSIS,
            category="deterministic_url_analysis",
            severity=self._derive_severity(result.indicators),
            confidence=1.0,
            description=self._build_description(result.indicators),
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
        result: dict[str, Any],
    ) -> EvidenceContract:
        """Build DNS evidence."""

        status = AnalysisStatus(result["status"])

        return EvidenceContract(
            investigation_id=investigation_id,
            type=EvidenceType.FORENSIC_ARTIFACT,
            category="dns_intelligence",
            severity=(
                SeverityLevel.INFORMATIONAL
                if status == AnalysisStatus.SUCCESS
                else SeverityLevel.INFORMATIONAL
            ),
            confidence=1.0 if status == AnalysisStatus.SUCCESS else 0.0,
            description=(
                f"DNS resolution returned "
                f"{result.get('address_count', 0)} address(es)."
                if status == AnalysisStatus.SUCCESS
                else "DNS intelligence did not produce a verified resolution."
            ),
            source_type="network",
            source_name="dns_intelligence",
            source_version="1.0.0",
            status=status,
            raw_payload=result,
            metadata={
                "hostname": result.get("hostname"),
                "addresses": result.get("addresses", []),
            },
        )

    @staticmethod
    def _build_tls_evidence(
        investigation_id: Any,
        result: dict[str, Any],
    ) -> EvidenceContract:
        """Build TLS evidence."""

        status = AnalysisStatus(result["status"])
        certificate_valid = result.get("certificate_valid")

        if status == AnalysisStatus.SUCCESS:
            if certificate_valid is True:
                description = (
                    "TLS certificate was retrieved and the hostname "
                    "was successfully verified."
                )
                severity = SeverityLevel.INFORMATIONAL
            else:
                description = (
                    "TLS certificate was retrieved, but certificate "
                    "validity could not be confirmed."
                )
                severity = SeverityLevel.MEDIUM
        else:
            description = (
                "TLS inspection did not produce a verified certificate "
                "conclusion."
            )
            severity = SeverityLevel.INFORMATIONAL

        return EvidenceContract(
            investigation_id=investigation_id,
            type=EvidenceType.FORENSIC_ARTIFACT,
            category="tls_intelligence",
            severity=severity,
            confidence=1.0 if status == AnalysisStatus.SUCCESS else 0.0,
            description=description,
            source_type="network",
            source_name="tls_intelligence",
            source_version="1.0.0",
            status=status,
            raw_payload=result,
            metadata={
                "hostname": result.get("hostname"),
                "port": result.get("port"),
                "tls_version": result.get("tls_version"),
                "certificate_valid": certificate_valid,
            },
        )

    @staticmethod
    def _build_http_evidence(
        investigation_id: Any,
        result: dict[str, Any],
    ) -> EvidenceContract:
        """Build HTTP intelligence evidence."""

        status = AnalysisStatus(result["status"])

        if status == AnalysisStatus.SUCCESS:
            indicators = result.get("indicators", [])

            if indicators:
                description = (
                    "HTTP intelligence detected the following indicators: "
                    f"{', '.join(indicators)}."
                )
                severity = URLIntelligenceTool._derive_http_severity(
                    indicators
                )
            else:
                description = (
                    "HTTP intelligence completed without detecting "
                    "specific HTTP-layer indicators."
                )
                severity = SeverityLevel.INFORMATIONAL

            confidence = 1.0
        else:
            description = (
                "HTTP intelligence did not produce a verified network "
                "response."
            )
            severity = SeverityLevel.INFORMATIONAL
            confidence = 0.0

        return EvidenceContract(
            investigation_id=investigation_id,
            type=EvidenceType.FORENSIC_ARTIFACT,
            category="http_intelligence",
            severity=severity,
            confidence=confidence,
            description=description,
            source_type="network",
            source_name="http_intelligence",
            source_version="1.0.0",
            status=status,
            raw_payload=result,
            metadata={
                "status_code": result.get("status_code"),
                "final_url": result.get("final_url"),
                "redirect_count": result.get("redirect_count"),
                "indicators": result.get("indicators", []),
                "https_to_http_downgrade": result.get(
                    "https_to_http_downgrade",
                    False,
                ),
            },
        )

    @staticmethod
    def _derive_severity(indicators: list[str]) -> SeverityLevel:
        """Derive severity from deterministic URL indicators."""

        high_indicators = {
            "embedded_credentials",
            "ip_address_host",
            "punycode_hostname",
        }

        medium_indicators = {
            "deep_subdomain_structure",
            "explicit_nonstandard_port",
            "very_long_url",
            "high_special_character_count",
            "suspicious_keywords",
        }

        if any(indicator in high_indicators for indicator in indicators):
            return SeverityLevel.HIGH

        if any(indicator in medium_indicators for indicator in indicators):
            return SeverityLevel.MEDIUM

        if "insecure_http" in indicators:
            return SeverityLevel.LOW

        return SeverityLevel.INFORMATIONAL

    @staticmethod
    def _derive_http_severity(indicators: list[str]) -> SeverityLevel:
        """Derive severity from HTTP-layer indicators."""

        if "https_to_http_downgrade" in indicators:
            return SeverityLevel.HIGH

        if "multiple_redirects" in indicators:
            return SeverityLevel.MEDIUM

        if "client_error_response" in indicators:
            return SeverityLevel.LOW

        if "server_error_response" in indicators:
            return SeverityLevel.LOW

        return SeverityLevel.INFORMATIONAL

    @staticmethod
    def _build_description(indicators: list[str]) -> str:
        """Build deterministic URL evidence description."""

        if not indicators:
            return "No suspicious URL structure indicators were detected."

        return (
            "Deterministic URL analysis detected the following indicators: "
            f"{', '.join(indicators)}."
        )