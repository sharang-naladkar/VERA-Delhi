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
from app.providers.sebi_dataset_provider import SEBIDatasetLookup


class RegistryRegulatoryProvider(RegulatoryVerificationProvider):
    """Resolve regulatory sources and query configured local SEBI snapshots."""

    _DATASET_SOURCE_IDS = {
        RegulatoryParticipantType.INVESTMENT_ADVISER:
            "sebi_investment_adviser_dataset",
        RegulatoryParticipantType.PORTFOLIO_MANAGER:
            "sebi_portfolio_manager_dataset",
        RegulatoryParticipantType.RESEARCH_ANALYST:
            "sebi_research_analyst_dataset",
    }

    def __init__(
        self,
        registry: RegulatorySourceRegistry | None = None,
        dataset_lookup: SEBIDatasetLookup | None = None,
    ) -> None:
        self._registry = registry or RegulatorySourceRegistry()
        self._dataset_lookup = dataset_lookup or SEBIDatasetLookup()

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
        """Report registry health without claiming live website connectivity."""
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
                "Local snapshot lookup may be configured; live source "
                "accessibility has not been checked."
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

    def _enabled_dataset_source(
        self,
        participant_type: RegulatoryParticipantType,
    ) -> RegulatorySource | None:
        """Return a compatible snapshot source only when it is enabled."""
        source_id = self._DATASET_SOURCE_IDS.get(participant_type)
        if source_id is None:
            return None

        enabled_sources = self._registry.list_sources(enabled_only=True)
        enabled_ids = {source.source_id for source in enabled_sources}

        if source_id not in enabled_ids:
            return None

        source = self._registry.get_source(source_id)
        if source is None or not source.enabled:
            return None

        if participant_type not in source.participant_types:
            return None

        return source

    async def verify(
        self,
        request: RegulatoryVerificationRequest,
    ) -> RegulatoryVerificationResult:
        """Use local snapshots where registered; never imply live verification."""
        capability = self._required_capability(request)

        # Resolve the registry sources first. Exceptions must propagate to the
        # verification service, which converts them into structured failures.
        candidates = self.select_sources(
            request.participant_type,
            capability,
        )

        dataset_source = self._enabled_dataset_source(request.participant_type)

        if dataset_source is not None:
            result = await self._dataset_lookup.verify(request)

            if result is not None:
                if (
                    result.source_id != dataset_source.source_id
                    or result.source_url != dataset_source.url
                    or result.participant_type != request.participant_type
                ):
                    return RegulatoryVerificationResult(
                        participant_type=request.participant_type,
                        status=AnalysisStatus.UNAVAILABLE,
                        subject_name=(
                            request.subject_name or request.organization_name
                        ),
                        registration_number=request.registration_number,
                        source_id=dataset_source.source_id,
                        source_url=dataset_source.url,
                        matched=None,
                        explanation=(
                            "The local snapshot reader returned source "
                            "metadata inconsistent with the source registry."
                        ),
                        limitations=[
                            "No result from the mismatched source was accepted.",
                            "No live SEBI verification occurred.",
                            "This result does not establish registration or fraud.",
                        ],
                    )

                return result

        if not candidates:
            return RegulatoryVerificationResult(
                participant_type=request.participant_type,
                status=AnalysisStatus.UNAVAILABLE,
                subject_name=(
                    request.subject_name or request.organization_name
                ),
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
                subject_name=(
                    request.subject_name or request.organization_name
                ),
                registration_number=request.registration_number,
                source_id=source.source_id,
                source_url=source.url,
                matched=None,
                explanation=(
                    "A compatible source is registered, but automated "
                    "retrieval is not enabled for it. No verification occurred."
                ),
                limitations=[
                    f"Required capability: {capability.value}.",
                    "The registry contains source metadata only for this lookup.",
                    "No authoritative record was retrieved or matched.",
                    "Manual review of the official source may be required.",
                ],
            )

        return RegulatoryVerificationResult(
            participant_type=request.participant_type,
            status=AnalysisStatus.UNAVAILABLE,
            subject_name=(
                request.subject_name or request.organization_name
            ),
            registration_number=request.registration_number,
            source_id=source.source_id,
            source_url=source.url,
            matched=None,
            explanation=(
                "A compatible source is configured for automated access, "
                "but no live retrieval adapter is implemented. "
                "No verification occurred."
            ),
            limitations=[
                f"Required capability: {capability.value}.",
                "No authoritative record was retrieved or matched.",
            ],
        )
