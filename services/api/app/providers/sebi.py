"""SEBI regulatory intelligence provider interfaces and fail-safe implementations."""

from abc import abstractmethod
from typing import Any

from app.contracts.sebi import VerificationResult, VerificationStatus
from app.contracts.status import AnalysisStatus
from app.providers.base import BaseProvider


class SEBIProvider(BaseProvider):
    """Interface for SEBI regulatory knowledge and entity verification."""

    @abstractmethod
    async def verify_entity(
        self,
        entity_name: str | None = None,
        registration_number: str | None = None,
        entity_type: str | None = None,
        claimed_organization: str | None = None,
    ) -> VerificationResult:
        """Verify a regulatory entity against a configured authoritative source."""
        raise NotImplementedError


class UnavailableSEBIProvider(SEBIProvider):
    """Fail-safe SEBI provider used when no authoritative backend is configured."""

    @property
    def provider_name(self) -> str:
        return "unavailable_sebi"

    @property
    def is_available(self) -> bool:
        return False

    async def health_check(self) -> dict[str, Any]:
        return {
            "status": AnalysisStatus.UNAVAILABLE.value,
            "provider": self.provider_name,
            "message": "SEBI regulatory data provider is not configured.",
        }

    async def verify_entity(
        self,
        entity_name: str | None = None,
        registration_number: str | None = None,
        entity_type: str | None = None,
        claimed_organization: str | None = None,
    ) -> VerificationResult:
        return VerificationResult(
            status=VerificationStatus.UNAVAILABLE,
            entity_name=entity_name,
            registration_number=registration_number,
            entity_type=entity_type,
            claimed_organization=claimed_organization,
            details="Authoritative SEBI verification source is unavailable.",
            metadata={
                "provider": self.provider_name,
                "source_available": False,
            },
        )


class MockSEBIProvider(SEBIProvider):
    """Deterministic provider for tests; contains no real SEBI records."""

    def __init__(
        self,
        *,
        status: VerificationStatus = VerificationStatus.VERIFIED,
        entity_name: str | None = None,
        registration_number: str | None = None,
        entity_type: str | None = None,
        claimed_organization: str | None = None,
    ) -> None:
        self._status = status
        self._entity_name = entity_name
        self._registration_number = registration_number
        self._entity_type = entity_type
        self._claimed_organization = claimed_organization

    @property
    def provider_name(self) -> str:
        return "mock_sebi"

    @property
    def is_available(self) -> bool:
        return True

    async def health_check(self) -> dict[str, Any]:
        return {
            "status": AnalysisStatus.SUCCESS.value,
            "provider": self.provider_name,
            "message": "Deterministic mock SEBI provider.",
        }

    async def verify_entity(
        self,
        entity_name: str | None = None,
        registration_number: str | None = None,
        entity_type: str | None = None,
        claimed_organization: str | None = None,
    ) -> VerificationResult:
        return VerificationResult(
            status=self._status,
            entity_name=entity_name or self._entity_name,
            registration_number=registration_number or self._registration_number,
            entity_type=entity_type or self._entity_type,
            claimed_organization=(
                claimed_organization or self._claimed_organization
            ),
            details=(
                "Deterministic mock response; "
                "not a live SEBI registry result."
            ),
            metadata={
                "provider": self.provider_name,
                "source_available": True,
                "test_fixture": True,
            },
        )