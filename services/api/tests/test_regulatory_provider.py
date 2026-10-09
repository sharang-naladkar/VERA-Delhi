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
    assert result["enabled_source_count"] == 6
    assert result["automated_source_ids"] == []


def test_provider_is_available_when_enabled_sources_exist():
    provider = RegistryRegulatoryProvider()

    assert provider.is_available is True
    assert len(provider.supported_source_ids) == 6


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
async def test_verify_does_not_claim_registration_without_live_access():
    provider = RegistryRegulatoryProvider()
    request = RegulatoryVerificationRequest(
        participant_type=RegulatoryParticipantType.INVESTMENT_ADVISER,
        subject_name="Example Adviser",
    )

    result = await provider.verify(request)

    assert result.status == AnalysisStatus.UNAVAILABLE
    assert result.matched is None
    assert result.source_id is not None
    assert result.source_url is not None
    assert result.evidence == []
    assert any("No authoritative record" in item for item in result.limitations)


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
