"""Tests for capability-aware regulatory source selection."""

from app.contracts.regulatory import (
    RegulatoryCapability,
    RegulatoryParticipantType,
    RegulatorySource,
    RegulatorySourceKind,
)
from app.providers.regulatory_provider import RegistryRegulatoryProvider
from app.providers.regulatory_source_registry import RegulatorySourceRegistry


def make_source(
    source_id: str,
    participant_type: RegulatoryParticipantType,
    capabilities: tuple[RegulatoryCapability, ...],
    *,
    enabled: bool = True,
    automated_access: bool = False,
) -> RegulatorySource:
    return RegulatorySource(
        source_id=source_id,
        name=f"Test source {source_id}",
        authority="Test authority",
        url=f"https://example.org/{source_id}",
        kind=RegulatorySourceKind.REGULATOR,
        participant_types=(participant_type,),
        capabilities=capabilities,
        enabled=enabled,
        automated_access=automated_access,
    )


def test_select_sources_matches_participant_and_capability():
    source = make_source(
        "ia_registration",
        RegulatoryParticipantType.INVESTMENT_ADVISER,
        (RegulatoryCapability.REGISTRATION_LOOKUP,),
    )
    registry = RegulatorySourceRegistry([source])
    provider = RegistryRegulatoryProvider(registry)

    selected = provider.select_sources(
        RegulatoryParticipantType.INVESTMENT_ADVISER,
        RegulatoryCapability.REGISTRATION_LOOKUP,
    )

    assert [item.source_id for item in selected] == ["ia_registration"]


def test_select_sources_excludes_wrong_capability():
    source = make_source(
        "ia_identity",
        RegulatoryParticipantType.INVESTMENT_ADVISER,
        (RegulatoryCapability.IDENTITY_MATCH,),
    )
    provider = RegistryRegulatoryProvider(
        RegulatorySourceRegistry([source])
    )

    selected = provider.select_sources(
        RegulatoryParticipantType.INVESTMENT_ADVISER,
        RegulatoryCapability.REGISTRATION_LOOKUP,
    )

    assert selected == []


def test_select_sources_excludes_wrong_participant_type():
    source = make_source(
        "broker_membership",
        RegulatoryParticipantType.STOCKBROKER,
        (RegulatoryCapability.BROKER_MEMBERSHIP_LOOKUP,),
    )
    provider = RegistryRegulatoryProvider(
        RegulatorySourceRegistry([source])
    )

    selected = provider.select_sources(
        RegulatoryParticipantType.INVESTMENT_ADVISER,
        RegulatoryCapability.BROKER_MEMBERSHIP_LOOKUP,
    )

    assert selected == []


def test_select_sources_excludes_disabled_sources():
    source = make_source(
        "disabled_ia",
        RegulatoryParticipantType.INVESTMENT_ADVISER,
        (RegulatoryCapability.REGISTRATION_LOOKUP,),
        enabled=False,
    )
    provider = RegistryRegulatoryProvider(
        RegulatorySourceRegistry([source])
    )

    selected = provider.select_sources(
        RegulatoryParticipantType.INVESTMENT_ADVISER,
        RegulatoryCapability.REGISTRATION_LOOKUP,
    )

    assert selected == []


def test_select_sources_returns_empty_when_registry_is_empty():
    provider = RegistryRegulatoryProvider(RegulatorySourceRegistry([]))

    selected = provider.select_sources(
        RegulatoryParticipantType.INVESTMENT_ADVISER,
        RegulatoryCapability.REGISTRATION_LOOKUP,
    )

    assert selected == []
