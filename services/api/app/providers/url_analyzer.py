"""Deterministic URL intelligence provider for VERA Phase 04."""

from __future__ import annotations

import ipaddress
import re
from urllib.parse import parse_qsl, urlsplit

from pydantic import BaseModel, Field


class URLAnalysisResult(BaseModel):
    """Structured, explainable URL analysis result."""

    is_valid: bool
    normalized_url: str | None = None
    scheme: str | None = None
    hostname: str | None = None
    port: int | None = None
    path: str | None = None
    query_parameter_count: int = 0
    fragment_present: bool = False

    url_length: int = 0
    hostname_length: int = 0
    subdomain_count: int = 0

    has_ip_host: bool = False
    has_punycode: bool = False
    has_credentials: bool = False
    has_explicit_port: bool = False

    special_character_count: int = 0
    suspicious_keyword_hits: list[str] = Field(default_factory=list)

    indicators: list[str] = Field(default_factory=list)
    warnings: list[str] = Field(default_factory=list)


class URLAnalyzer:
    """Performs deterministic, network-free URL analysis."""

    _SUSPICIOUS_KEYWORDS = (
        "login",
        "signin",
        "verify",
        "verification",
        "secure",
        "account",
        "wallet",
        "investment",
        "invest",
        "trading",
        "broker",
        "profit",
        "bonus",
        "reward",
        "claim",
        "kyc",
        "refund",
        "payment",
        "upi",
        "bank",
        "password",
        "otp",
    )

    _SPECIAL_CHARACTERS = re.compile(r"[@%_\-]")

    def analyze(self, url: str) -> URLAnalysisResult:
        """Analyze a URL without performing network access."""

        if not isinstance(url, str) or not url.strip():
            return URLAnalysisResult(
                is_valid=False,
                warnings=["URL input is empty."],
            )

        raw_url = url.strip()

        try:
            parsed = urlsplit(raw_url)
        except ValueError as exc:
            return URLAnalysisResult(
                is_valid=False,
                warnings=[f"URL parsing failed: {exc}"],
            )

        if parsed.scheme.lower() not in {"http", "https"}:
            return URLAnalysisResult(
                is_valid=False,
                warnings=["URL must use HTTP or HTTPS."],
            )

        if not parsed.hostname:
            return URLAnalysisResult(
                is_valid=False,
                warnings=["URL does not contain a hostname."],
            )

        try:
            hostname = parsed.hostname.lower().rstrip(".")
            port = parsed.port
        except ValueError as exc:
            return URLAnalysisResult(
                is_valid=False,
                warnings=[f"URL port is invalid: {exc}"],
            )

        normalized_url = self._normalize(parsed, hostname)

        query_parameters = parse_qsl(
            parsed.query,
            keep_blank_values=True,
        )

        suspicious_keyword_hits = self._find_suspicious_keywords(
            raw_url.lower()
        )

        indicators: list[str] = []

        has_ip_host = self._is_ip_address(hostname)
        has_punycode = any(
            label.startswith("xn--")
            for label in hostname.split(".")
        )
        has_credentials = bool(parsed.username or parsed.password)
        has_explicit_port = parsed.port is not None

        # Explicitly supplied ports are not necessarily suspicious.
        # 80 is the standard HTTP port and 443 is the standard HTTPS port.
        has_nonstandard_port = (
            has_explicit_port
            and port not in {80, 443}
        )

        # IP addresses are hosts, not domain names, so they cannot have
        # meaningful subdomains.
        subdomain_count = (
            0 if has_ip_host else self._subdomain_count(hostname)
        )

        if parsed.scheme.lower() == "http":
            indicators.append("insecure_http")

        if has_ip_host:
            indicators.append("ip_address_host")

        if has_punycode:
            indicators.append("punycode_hostname")

        if has_credentials:
            indicators.append("embedded_credentials")

        if has_nonstandard_port:
            indicators.append("explicit_nonstandard_port")

        if suspicious_keyword_hits:
            indicators.append("suspicious_keywords")

        if subdomain_count >= 3:
            indicators.append("deep_subdomain_structure")

        if len(raw_url) >= 120:
            indicators.append("very_long_url")
        elif len(raw_url) >= 80:
            indicators.append("long_url")

        special_character_count = len(
            self._SPECIAL_CHARACTERS.findall(raw_url)
        )

        if special_character_count >= 10:
            indicators.append("high_special_character_count")

        warnings: list[str] = []

        if parsed.fragment:
            warnings.append(
                "URL contains a fragment; fragment content is not sent "
                "to the server."
            )

        return URLAnalysisResult(
            is_valid=True,
            normalized_url=normalized_url,
            scheme=parsed.scheme.lower(),
            hostname=hostname,
            port=port,
            path=parsed.path or "/",
            query_parameter_count=len(query_parameters),
            fragment_present=bool(parsed.fragment),
            url_length=len(raw_url),
            hostname_length=len(hostname),
            subdomain_count=subdomain_count,
            has_ip_host=has_ip_host,
            has_punycode=has_punycode,
            has_credentials=has_credentials,
            has_explicit_port=has_explicit_port,
            special_character_count=special_character_count,
            suspicious_keyword_hits=suspicious_keyword_hits,
            indicators=indicators,
            warnings=warnings,
        )

    @staticmethod
    def _normalize(parsed, hostname: str) -> str:
        """Build a stable normalized URL representation."""

        scheme = parsed.scheme.lower()

        if parsed.port is not None:
            netloc = f"{hostname}:{parsed.port}"
        else:
            netloc = hostname

        if parsed.username is not None:
            credentials = parsed.username

            if parsed.password is not None:
                credentials += f":{parsed.password}"

            netloc = f"{credentials}@{netloc}"

        path = parsed.path or "/"

        normalized = f"{scheme}://{netloc}{path}"

        if parsed.query:
            normalized += f"?{parsed.query}"

        if parsed.fragment:
            normalized += f"#{parsed.fragment}"

        return normalized

    @staticmethod
    def _is_ip_address(hostname: str) -> bool:
        """Return True when hostname is an IPv4 or IPv6 address."""

        try:
            ipaddress.ip_address(hostname)
            return True
        except ValueError:
            return False

    @staticmethod
    def _subdomain_count(hostname: str) -> int:
        """Count hostname labels preceding the registrable-domain pair."""

        labels = [label for label in hostname.split(".") if label]

        if len(labels) <= 2:
            return 0

        return len(labels) - 2

    def _find_suspicious_keywords(self, value: str) -> list[str]:
        """Return unique suspicious keywords found in the URL."""

        hits: list[str] = []

        for keyword in self._SUSPICIOUS_KEYWORDS:
            if re.search(
                rf"(?<![a-z]){re.escape(keyword)}(?![a-z])",
                value,
            ):
                hits.append(keyword)

        return hits