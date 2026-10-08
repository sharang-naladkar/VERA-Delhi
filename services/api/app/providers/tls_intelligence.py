"""TLS intelligence provider for VERA URL investigations."""

from __future__ import annotations

import asyncio
import socket
import ssl
from datetime import datetime, timezone
from typing import Any
from uuid import UUID

from app.contracts.status import AnalysisStatus
from app.providers.base import BaseProvider


class TLSIntelligenceProvider(BaseProvider):
    """Retrieve and validate TLS certificate metadata for HTTPS hosts."""

    DEFAULT_TIMEOUT_SECONDS = 8.0

    @property
    def provider_name(self) -> str:
        return "tls_intelligence"

    @property
    def is_available(self) -> bool:
        """Return whether the local Python runtime provides TLS support."""
        return hasattr(ssl, "create_default_context")

    async def health_check(self) -> dict[str, Any]:
        """Return provider availability without performing a network lookup."""
        if not self.is_available:
            return {
                "status": AnalysisStatus.UNAVAILABLE.value,
                "provider": self.provider_name,
                "message": "Python TLS support is unavailable.",
            }

        return {
            "status": AnalysisStatus.SUCCESS.value,
            "provider": self.provider_name,
            "message": "Python TLS support is available.",
        }

    async def inspect_certificate(
        self,
        investigation_id: UUID,
        hostname: str,
        port: int = 443,
        timeout_seconds: float = DEFAULT_TIMEOUT_SECONDS,
    ) -> dict[str, Any]:
        """Inspect the TLS certificate presented by an HTTPS endpoint."""

        base_result = {
            "provider": self.provider_name,
            "investigation_id": str(investigation_id),
            "hostname": hostname,
            "port": port,
        }

        if not hostname or not hostname.strip():
            return {
                **base_result,
                "status": AnalysisStatus.FAILED.value,
                "error": "Hostname is missing.",
            }

        if not self.is_available:
            return {
                **base_result,
                "status": AnalysisStatus.UNAVAILABLE.value,
                "error": "Python TLS support is unavailable.",
            }

        normalized_hostname = hostname.strip().lower().rstrip(".")

        if not 1 <= port <= 65535:
            return {
                **base_result,
                "hostname": normalized_hostname,
                "status": AnalysisStatus.FAILED.value,
                "error": "Port must be between 1 and 65535.",
            }

        try:
            result = await asyncio.to_thread(
                self._inspect_certificate_sync,
                normalized_hostname,
                port,
                timeout_seconds,
            )

            return {
                **base_result,
                "hostname": normalized_hostname,
                **result,
            }

        except ssl.CertificateError as exc:
            return {
                **base_result,
                "hostname": normalized_hostname,
                "status": AnalysisStatus.FAILED.value,
                "hostname_verified": False,
                "error": f"TLS certificate hostname verification failed: {exc}",
            }

        except (ssl.SSLError, socket.timeout, TimeoutError, OSError) as exc:
            return {
                **base_result,
                "hostname": normalized_hostname,
                "status": AnalysisStatus.FAILED.value,
                "error": f"TLS connection failed: {exc}",
            }

        except Exception as exc:
            return {
                **base_result,
                "hostname": normalized_hostname,
                "status": AnalysisStatus.FAILED.value,
                "error": f"TLS inspection failed: {exc}",
            }

    def _inspect_certificate_sync(
        self,
        hostname: str,
        port: int,
        timeout_seconds: float,
    ) -> dict[str, Any]:
        """Perform synchronous TLS inspection."""

        context = ssl.create_default_context()

        with socket.create_connection(
            (hostname, port),
            timeout=timeout_seconds,
        ) as raw_socket:
            with context.wrap_socket(
                raw_socket,
                server_hostname=hostname,
            ) as tls_socket:
                certificate = tls_socket.getpeercert()

                if not certificate:
                    return {
                        "status": AnalysisStatus.FAILED.value,
                        "hostname_verified": False,
                        "error": "TLS peer certificate was not provided.",
                    }

                not_before = self._parse_certificate_date(
                    certificate.get("notBefore")
                )
                not_after = self._parse_certificate_date(
                    certificate.get("notAfter")
                )

                now = datetime.now(timezone.utc)

                certificate_valid = bool(
                    not_before
                    and not_after
                    and not_before <= now <= not_after
                )

                subject = self._flatten_name(
                    certificate.get("subject", ())
                )
                issuer = self._flatten_name(
                    certificate.get("issuer", ())
                )

                san_values = [
                    value
                    for key, value in certificate.get("subjectAltName", ())
                    if key == "DNS"
                ]

                return {
                    "status": AnalysisStatus.SUCCESS.value,
                    "hostname_verified": True,
                    "certificate_valid": certificate_valid,
                    "not_before": (
                        not_before.isoformat() if not_before else None
                    ),
                    "not_after": (
                        not_after.isoformat() if not_after else None
                    ),
                    "subject": subject,
                    "issuer": issuer,
                    "subject_alt_names": san_values,
                    "tls_version": tls_socket.version(),
                    "cipher": tls_socket.cipher(),
                }

    @staticmethod
    def _parse_certificate_date(value: str | None) -> datetime | None:
        """Parse an OpenSSL certificate timestamp into UTC."""

        if not value:
            return None

        try:
            parsed = datetime.strptime(
                value,
                "%b %d %H:%M:%S %Y %Z",
            )

            return parsed.replace(tzinfo=timezone.utc)

        except ValueError:
            return None

    @staticmethod
    def _flatten_name(name: tuple[Any, ...]) -> dict[str, list[str]]:
        """Convert an ssl certificate name structure into a simple mapping."""

        flattened: dict[str, list[str]] = {}

        for relative_name in name:
            for key, value in relative_name:
                flattened.setdefault(key, []).append(value)

        return flattened