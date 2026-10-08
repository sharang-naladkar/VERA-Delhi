"""HTTP intelligence provider for VERA URL investigations."""

from __future__ import annotations

import asyncio
import time
from typing import Any
from uuid import UUID

import httpx

from app.contracts.status import AnalysisStatus
from app.providers.base import BaseProvider


class HTTPIntelligenceProvider(BaseProvider):
    """Inspect HTTP(S) metadata without making a fraud determination."""

    DEFAULT_TIMEOUT_SECONDS = 10.0
    DEFAULT_MAX_REDIRECTS = 5

    @property
    def provider_name(self) -> str:
        return "http_intelligence"

    @property
    def is_available(self) -> bool:
        """Return whether the HTTP client dependency is available."""
        return True

    async def health_check(self) -> dict[str, Any]:
        """Return provider availability without making a network request."""
        return {
            "status": AnalysisStatus.SUCCESS.value,
            "provider": self.provider_name,
            "message": "HTTP intelligence provider is available.",
        }

    async def inspect_url(
        self,
        investigation_id: UUID,
        url: str,
        timeout_seconds: float = DEFAULT_TIMEOUT_SECONDS,
        max_redirects: int = DEFAULT_MAX_REDIRECTS,
    ) -> dict[str, Any]:
        """Inspect HTTP metadata and redirect behavior for a URL."""

        base_result = {
            "provider": self.provider_name,
            "investigation_id": str(investigation_id),
            "url": url,
        }

        if not url or not url.strip():
            return {
                **base_result,
                "status": AnalysisStatus.FAILED.value,
                "error": "URL is missing.",
            }

        if timeout_seconds <= 0:
            return {
                **base_result,
                "status": AnalysisStatus.FAILED.value,
                "error": "Timeout must be greater than zero.",
            }

        if max_redirects < 0:
            return {
                **base_result,
                "status": AnalysisStatus.FAILED.value,
                "error": "Maximum redirects cannot be negative.",
            }

        normalized_url = url.strip()

        try:
            result = await asyncio.to_thread(
                self._inspect_url_sync,
                normalized_url,
                timeout_seconds,
                max_redirects,
            )

            return {
                **base_result,
                "url": normalized_url,
                **result,
            }

        except httpx.TimeoutException as exc:
            return {
                **base_result,
                "url": normalized_url,
                "status": AnalysisStatus.FAILED.value,
                "error": f"HTTP request timed out: {exc}",
            }

        except httpx.HTTPError as exc:
            return {
                **base_result,
                "url": normalized_url,
                "status": AnalysisStatus.FAILED.value,
                "error": f"HTTP request failed: {exc}",
            }

        except Exception as exc:
            return {
                **base_result,
                "url": normalized_url,
                "status": AnalysisStatus.FAILED.value,
                "error": f"HTTP inspection failed: {exc}",
            }

    def _inspect_url_sync(
        self,
        url: str,
        timeout_seconds: float,
        max_redirects: int,
    ) -> dict[str, Any]:
        """Perform synchronous HTTP inspection."""

        start_time = time.perf_counter()

        timeout = httpx.Timeout(timeout_seconds)

        with httpx.Client(
            timeout=timeout,
            follow_redirects=True,
            max_redirects=max_redirects,
            headers={
                "User-Agent": (
                    "VERA-URL-Intelligence/1.0 "
                    "(security-research)"
                )
            },
        ) as client:
            response = client.get(url)

        elapsed_ms = round(
            (time.perf_counter() - start_time) * 1000,
            2,
        )

        history = [
            {
                "status_code": redirect.status_code,
                "url": str(redirect.url),
                "location": redirect.headers.get("location"),
            }
            for redirect in response.history
        ]

        final_url = str(response.url)

        headers = {
            key.lower(): value
            for key, value in response.headers.items()
        }

        content_type = headers.get("content-type")
        content_length = headers.get("content-length")
        server = headers.get("server")

        title = self._extract_html_title(
            response.text,
            content_type,
        )

        initial_scheme = url.split(":", 1)[0].lower()
        final_scheme = response.url.scheme.lower()

        https_to_http_downgrade = (
            initial_scheme == "https"
            and final_scheme == "http"
        )

        return {
            "status": AnalysisStatus.SUCCESS.value,
            "status_code": response.status_code,
            "final_url": final_url,
            "redirect_count": len(response.history),
            "redirect_chain": history,
            "response_headers": headers,
            "content_type": content_type,
            "content_length": self._parse_content_length(content_length),
            "server": server,
            "html_title": title,
            "response_time_ms": elapsed_ms,
            "https_to_http_downgrade": https_to_http_downgrade,
            "indicators": self._derive_indicators(
                response.status_code,
                response.history,
                https_to_http_downgrade,
                content_type,
            ),
        }

    @staticmethod
    def _extract_html_title(
        body: str,
        content_type: str | None,
    ) -> str | None:
        """Extract a simple HTML title without external parsing dependencies."""

        if not body:
            return None

        if not content_type or "text/html" not in content_type.lower():
            return None

        lowered = body.lower()
        start_marker = "<title>"
        end_marker = "</title>"

        start = lowered.find(start_marker)

        if start == -1:
            return None

        start += len(start_marker)
        end = lowered.find(end_marker, start)

        if end == -1:
            return None

        title = body[start:end].strip()

        return title[:500] if title else None

    @staticmethod
    def _parse_content_length(value: str | None) -> int | None:
        """Parse the Content-Length header when it contains an integer."""

        if not value:
            return None

        try:
            return int(value)
        except ValueError:
            return None

    @staticmethod
    def _derive_indicators(
        status_code: int,
        history: list[httpx.Response],
        https_to_http_downgrade: bool,
        content_type: str | None,
    ) -> list[str]:
        """Derive deterministic HTTP indicators."""

        indicators: list[str] = []

        if 400 <= status_code <= 499:
            indicators.append("client_error_response")

        if 500 <= status_code <= 599:
            indicators.append("server_error_response")

        if len(history) >= 3:
            indicators.append("multiple_redirects")

        if https_to_http_downgrade:
            indicators.append("https_to_http_downgrade")

        if content_type and "text/html" in content_type.lower():
            indicators.append("html_response")

        return indicators