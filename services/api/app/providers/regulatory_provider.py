"""Regulatory verification provider with explicit source selection."""

from typing import Any

from app.contracts.regulatory import (
    RegulatoryCapability,
    RegulatoryParticipantType,
    RegulatorySource,
    RegulatoryVerificationRequest,
    RegulatoryVerificationResult,
)
from app.contracts.status import AnalysisStatus
from app.providers.regulatory_source_registry import RegulatorySourceRegistry
from app.providers.regulatory_verification import RegulatoryVerificationProvider


class RegistryRegulatoryProvider(RegulatoryVerificationProvider):
    """Resolve applicable regulatory sources without claiming live verification."""

    def __init__(
        self,
        registry: RegulatorySourceRegistry | None = None,
    ) -> None:
        self._registry = registry or RegulatorySourceRegistry()

    @property
    def provider_name(self) -> str:
        return "regulatory_registry"

    @property
    def is_available(self) -> bool:
        """The provider is available when at least one source is enabled."""
        return bool(self.supported_source_ids)

    @property
    def supported_source_ids(self) -> tuple[str, ...]:
        """Return enabled source IDs."""
        return tuple(
            source.source_id
            for source in self._registry.list_sources(enabled_only=True)
        )

    async def health_check(self) -> dict[str, Any]:
        """Report local registry health without making network requests."""
        sources = self._registry.list_sources(enabled_only=True)
        automated_sources = [
            source.source_id
            for source in sources
            if source.automated_access
        ]

        if not sources:
            return {
                "status": AnalysisStatus.UNAVAILABLE.value,
                "provider": self.provider_name,
                "message": "No enabled regulatory sources are configured.",
                "enabled_source_count": 0,
                "automated_source_ids": [],
                "live_source_access_checked": False,
            }

        return {
            "status": AnalysisStatus.SUCCESS.value,
            "provider": self.provider_name,
            "message": (
                "Regulatory source registry is available. "
                "Live source accessibility has not been checked."
            ),
            "enabled_source_count": len(sources),
            "automated_source_ids": automated_sources,
            "live_source_access_checked": False,
        }

    def select_sources(
        self,
        participant_type: RegulatoryParticipantType,
        capability: RegulatoryCapability,
    ) -> list[RegulatorySource]:
        """Return enabled sources matching participant type and capability."""
        return self._registry.sources_for(
            participant_type,
            capability=capability,
            enabled_only=True,
        )

    @staticmethod
    def _required_capability(
        request: RegulatoryVerificationRequest,
    ) -> RegulatoryCapability:
        """Choose the minimum registry capability for the supplied request."""
        if request.participant_type == RegulatoryParticipantType.STOCKBROKER:
            return RegulatoryCapability.BROKER_MEMBERSHIP_LOOKUP

        if (
            request.participant_type
            == RegulatoryParticipantType.AUTHORISED_PERSON
        ):
            return RegulatoryCapability.AUTHORISED_PERSON_LOOKUP

        if request.registration_number:
            return RegulatoryCapability.REGISTRATION_LOOKUP

        return RegulatoryCapability.IDENTITY_MATCH

    async def verify(
        self,
        request: RegulatoryVerificationRequest,
    ) -> RegulatoryVerificationResult:
        """Resolve a source but do not claim verification without retrieval."""
        capability = self._required_capability(request)
        candidates = self.select_sources(
            request.participant_type,
            capability,
        )

        if not candidates:
            return RegulatoryVerificationResult(
                participant_type=request.participant_type,
                status=AnalysisStatus.UNAVAILABLE,
                subject_name=request.subject_name,
                registration_number=request.registration_number,
                matched=None,
                explanation=(
                    "No enabled source advertises the required capability "
                    "for this participant type. No verification occurred."
                ),
                limitations=[
                    f"Required capability: {capability.value}.",
                    "No authoritative record was retrieved or matched.",
                    "This result does not establish registration or fraud.",
                ],
            )

        source = candidates[0]

        if not source.automated_access:
            return RegulatoryVerificationResult(
                participant_type=request.participant_type,
                status=AnalysisStatus.UNAVAILABLE,
                subject_name=request.subject_name,
                registration_number=request.registration_number,
                source_id=source.source_id,
                source_url=source.url,
                matched=None,
                explanation=(
                    "A compatible official source is registered, but "
                    "automated access is not enabled. No live verification "
                    "occurred."
                ),
                limitations=[
                    f"Required capability: {capability.value}.",
                    "The registry contains source metadata only.",
                    "No authoritative record was retrieved or matched.",
                    "Manual review of the official source may be required.",
                ],
            )

        return RegulatoryVerificationResult(
            participant_type=request.participant_type,
            status=AnalysisStatus.UNAVAILABLE,
            subject_name=request.subject_name,
            registration_number=request.registration_number,
            source_id=source.source_id,
            source_url=source.url,
            matched=None,
            explanation=(
                "A compatible source is configured for automated access, "
                "but no live retrieval adapter is implemented by this "
                "provider. No verification occurred."
            ),
            limitations=[
                f"Required capability: {capability.value}.",
                "No authoritative record was retrieved or matched.",
            ],
        )
