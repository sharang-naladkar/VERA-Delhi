"""Regulatory verification provider with explicit source availability."""

from typing import Any

from app.contracts.regulatory import (
    RegulatoryVerificationRequest,
    RegulatoryVerificationResult,
)
from app.contracts.status import AnalysisStatus
from app.providers.regulatory_source_registry import RegulatorySourceRegistry
from app.providers.regulatory_verification import RegulatoryVerificationProvider


class RegistryRegulatoryProvider(RegulatoryVerificationProvider):
    """Provider that reports configured source availability.

    This implementation does not retrieve regulatory records. It only
    reports whether registered sources are configured for automated access.
    """

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
        """The registry provider is available when it has enabled sources."""
        return bool(self.supported_source_ids)

    @property
    def supported_source_ids(self) -> tuple[str, ...]:
        """Return enabled sources declared in the source registry."""
        return tuple(
            source.source_id
            for source in self._registry.list_sources(enabled_only=True)
        )

    async def health_check(self) -> dict[str, Any]:
        """Report registry health without contacting external sources."""
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
            }

        return {
            "status": AnalysisStatus.SUCCESS.value,
            "provider": self.provider_name,
            "message": (
                "Regulatory source registry is available. "
                "This check does not confirm live source accessibility."
            ),
            "enabled_source_count": len(sources),
            "automated_source_ids": automated_sources,
            "live_source_access_checked": False,
        }

    async def verify(
        self,
        request: RegulatoryVerificationRequest,
    ) -> RegulatoryVerificationResult:
        """Fail safely until a live source adapter is implemented."""
        candidate_sources = self._registry.sources_for(
            request.participant_type,
            enabled_only=True,
        )

        if not candidate_sources:
            return RegulatoryVerificationResult(
                participant_type=request.participant_type,
                status=AnalysisStatus.UNAVAILABLE,
                subject_name=request.subject_name,
                registration_number=request.registration_number,
                matched=None,
                explanation=(
                    "No enabled regulatory source is configured for this "
                    "participant type. No registration verification occurred."
                ),
                limitations=[
                    "No authoritative source was queried.",
                    "This result does not establish that the participant "
                    "is registered or unregistered.",
                ],
            )

        automated_sources = [
            source
            for source in candidate_sources
            if source.automated_access
        ]

        if not automated_sources:
            source = candidate_sources[0]
            return RegulatoryVerificationResult(
                participant_type=request.participant_type,
                status=AnalysisStatus.UNAVAILABLE,
                subject_name=request.subject_name,
                registration_number=request.registration_number,
                source_id=source.source_id,
                source_url=source.url,
                matched=None,
                explanation=(
                    "A relevant source is registered, but automated access "
                    "has not been enabled. No live verification occurred."
                ),
                limitations=[
                    "The source registry contains metadata only.",
                    "No authoritative record was retrieved or matched.",
                    "Manual review of the official source may be required.",
                ],
            )

        source = automated_sources[0]
        return RegulatoryVerificationResult(
            participant_type=request.participant_type,
            status=AnalysisStatus.UNAVAILABLE,
            subject_name=request.subject_name,
            registration_number=request.registration_number,
            source_id=source.source_id,
            source_url=source.url,
            matched=None,
            explanation=(
                "The source is marked for automated access, but this provider "
                "does not yet implement a live retrieval adapter."
            ),
            limitations=[
                "Automated source access is configured but not implemented "
                "by this provider.",
                "No authoritative record was retrieved or matched.",
            ],
        )
