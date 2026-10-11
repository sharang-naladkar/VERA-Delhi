"""Tests for regulatory provider health and safe availability handling."""

import pytest

from app.contracts.regulatory import (
    RegulatoryParticipantType,
    RegulatorySource,
    RegulatorySourceKind,
    RegulatoryVerificationRequest,
)
from app.contracts.status import AnalysisStatus
from app.providers.regulatory_provider import RegistryRegulatoryProvider
from app.providers.regulatory_source_registry import RegulatorySourceRegistry


@pytest.mark.asyncio
async def test_health_check_reports_registry_available_without_live_access():
    provider = RegistryRegulatoryProvider()

    result = await provider.health_check()

    assert result["status"] == AnalysisStatus.SUCCESS.value
    assert result["provider"] == "regulatory_registry"
    assert result["live_source_access_checked"] is False
    assert result["enabled_source_count"] == 9
    assert result["automated_source_ids"] == []


def test_provider_is_available_when_enabled_sources_exist():
    provider = RegistryRegulatoryProvider()

    assert provider.is_available is True
    assert len(provider.supported_source_ids) == 9


def test_registry_contains_all_three_sebi_dataset_sources():
    registry = RegulatorySourceRegistry()

    expected_sources = {
        "sebi_investment_adviser_dataset",
        "sebi_portfolio_manager_dataset",
        "sebi_research_analyst_dataset",
    }

    actual_sources = {
        source.source_id
        for source in registry.list_sources()
    }

    assert expected_sources.issubset(actual_sources)


def test_portfolio_manager_dataset_source_has_expected_capabilities():
    registry = RegulatorySourceRegistry()

    source = registry.get_source("sebi_portfolio_manager_dataset")

    assert source is not None
    assert (
        RegulatoryParticipantType.PORTFOLIO_MANAGER
        in source.participant_types
    )
    assert source.url.startswith("https://")
    assert source.automated_access is False


def test_provider_is_unavailable_when_no_sources_are_enabled():
    registry = RegulatorySourceRegistry(
        [
            RegulatorySource(
                source_id="disabled_source",
                name="Disabled source",
                authority="Example authority",
                url="https://example.org/registry",
                kind=RegulatorySourceKind.REGULATOR,
                participant_types=(
                    RegulatoryParticipantType.INVESTMENT_ADVISER,
                ),
                capabilities=("registration_lookup",),
                enabled=False,
                automated_access=False,
            )
        ]
    )
    provider = RegistryRegulatoryProvider(registry)

    assert provider.is_available is False


@pytest.mark.asyncio
async def test_health_check_reports_unavailable_when_no_sources_are_enabled():
    registry = RegulatorySourceRegistry([])
    provider = RegistryRegulatoryProvider(registry)

    result = await provider.health_check()

    assert result["status"] == AnalysisStatus.UNAVAILABLE.value
    assert result["enabled_source_count"] == 0
    assert result["automated_source_ids"] == []


@pytest.mark.asyncio
async def test_verify_does_not_claim_registration_when_snapshot_is_unavailable():
    provider = RegistryRegulatoryProvider()
    request = RegulatoryVerificationRequest(
        participant_type=RegulatoryParticipantType.INVESTMENT_ADVISER,
        subject_name="Example Adviser",
    )

    result = await provider.verify(request)

    assert result.status == AnalysisStatus.UNAVAILABLE
    assert result.matched is None
    assert result.source_id == "sebi_investment_adviser_dataset"
    assert result.source_url is not None
    assert result.evidence == []

    assert any(
        "record-level verification" in item.lower()
        for item in result.limitations
    )
    assert any(
        "snapshot" in item.lower()
        for item in result.limitations
    )


@pytest.mark.asyncio
async def test_verify_returns_unavailable_for_unsupported_participant():
    provider = RegistryRegulatoryProvider()
    request = RegulatoryVerificationRequest(
        participant_type=RegulatoryParticipantType.FINFLUENCER,
        social_handle="@example",
    )

    result = await provider.verify(request)

    assert result.status == AnalysisStatus.UNAVAILABLE
    assert result.matched is None
    assert result.source_id is None
    assert result.source_url is None