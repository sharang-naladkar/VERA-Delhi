"""DNS intelligence provider for VERA URL investigations."""

import asyncio
import socket
from typing import Any
from uuid import UUID

from app.contracts.status import AnalysisStatus
from app.providers.base import BaseProvider


class DNSIntelligenceProvider(BaseProvider):
    """Resolves DNS records for a domain using the system resolver."""

    @property
    def provider_name(self) -> str:
        return "dns_intelligence"

    @property
    def is_available(self) -> bool:
        """The provider is available when the Python socket resolver is present."""
        return hasattr(socket, "getaddrinfo")

    async def health_check(self) -> dict[str, Any]:
        """Return provider availability without performing an external lookup."""
        if not self.is_available:
            return {
                "status": AnalysisStatus.UNAVAILABLE.value,
                "provider": self.provider_name,
                "message": "System DNS resolver is unavailable.",
            }

        return {
            "status": AnalysisStatus.SUCCESS.value,
            "provider": self.provider_name,
            "message": "System DNS resolver is available.",
        }

    async def resolve_domain(
        self,
        investigation_id: UUID,
        hostname: str,
    ) -> dict[str, Any]:
        """Resolve A/AAAA addresses for a hostname."""

        if not hostname or not hostname.strip():
            return {
                "status": AnalysisStatus.FAILED.value,
                "provider": self.provider_name,
                "investigation_id": str(investigation_id),
                "hostname": hostname,
                "addresses": [],
                "error": "Hostname is missing.",
            }

        if not self.is_available:
            return {
                "status": AnalysisStatus.UNAVAILABLE.value,
                "provider": self.provider_name,
                "investigation_id": str(investigation_id),
                "hostname": hostname,
                "addresses": [],
                "error": "System DNS resolver is unavailable.",
            }

        normalized_hostname = hostname.strip().lower().rstrip(".")

        try:
            records = await asyncio.to_thread(
                socket.getaddrinfo,
                normalized_hostname,
                None,
                socket.AF_UNSPEC,
                socket.SOCK_STREAM,
            )

            addresses = sorted(
                {
                    record[4][0]
                    for record in records
                    if record[4] and record[4][0]
                }
            )

            if not addresses:
                return {
                    "status": AnalysisStatus.FAILED.value,
                    "provider": self.provider_name,
                    "investigation_id": str(investigation_id),
                    "hostname": normalized_hostname,
                    "addresses": [],
                    "error": "DNS resolution returned no addresses.",
                }

            return {
                "status": AnalysisStatus.SUCCESS.value,
                "provider": self.provider_name,
                "investigation_id": str(investigation_id),
                "hostname": normalized_hostname,
                "addresses": addresses,
                "address_count": len(addresses),
            }

        except socket.gaierror as exc:
            return {
                "status": AnalysisStatus.FAILED.value,
                "provider": self.provider_name,
                "investigation_id": str(investigation_id),
                "hostname": normalized_hostname,
                "addresses": [],
                "error": f"DNS resolution failed: {exc}",
            }
        except OSError as exc:
            return {
                "status": AnalysisStatus.FAILED.value,
                "provider": self.provider_name,
                "investigation_id": str(investigation_id),
                "hostname": normalized_hostname,
                "addresses": [],
                "error": f"DNS resolution failed: {exc}",
            }