"""Tests for regulatory knowledge providers."""

import pytest

from app.contracts.regulatory import RegulatorySearchResponse
from app.contracts.status import AnalysisStatus
from app.providers.regulatory import (
    MockRegulatoryKnowledgeProvider,
    UnavailableRegulatoryKnowledgeProvider,
)


@pytest.mark.asyncio
async def test_unavailable_regulatory_provider() -> None:
    provider = UnavailableRegulatoryKnowledgeProvider()

    assert provider.is_available is False
    assert provider.provider_name == "unavailable_regulatory_knowledge"

    health = await provider.health_check()

    assert health["status"] == AnalysisStatus.UNAVAILABLE.value
    assert health["provider"] == provider.provider_name

    result = await provider.search(
        "investment adviser registration requirements",
    )

    assert result.status == AnalysisStatus.UNAVAILABLE.value
    assert result.source_available is False
    assert result.results == []
    assert result.metadata["provider"] == provider.provider_name


@pytest.mark.asyncio
async def test_mock_regulatory_provider() -> None:
    provider = MockRegulatoryKnowledgeProvider()

    assert provider.is_available is True
    assert provider.provider_name == "mock_regulatory_knowledge"

    health = await provider.health_check()

    assert health["status"] == AnalysisStatus.SUCCESS.value

    result = await provider.search(
        "investment adviser registration requirements",
    )

    assert isinstance(result, RegulatorySearchResponse)
    assert result.status == AnalysisStatus.SUCCESS.value
    assert result.source_available is True
    assert result.results == []
    assert result.metadata["test_fixture"] is True