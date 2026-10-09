"""Failure-path tests for the regulatory verification service."""

import pytest

from app.contracts.regulatory import (
    RegulatoryParticipantType,
    RegulatoryVerificationRequest,
    RegulatoryVerificationResult,
)
from app.contracts.status import AnalysisStatus
from app.providers.regulatory_provider import RegistryRegulatoryProvider
from app.providers.regulatory_result_validator import RegulatoryResultValidator
from app.providers.regulatory_source_registry import RegulatorySourceRegistry
from app.providers.regulatory_verification_service import (
    RegulatoryVerificationService,
)


def make_request():
    return RegulatoryVerificationRequest(
        participant_type=RegulatoryParticipantType.INVESTMENT_ADVISER,
        subject_name="Example Adviser",
    )


class RaisingProvider(RegistryRegulatoryProvider):
    async def verify(self, request):
        raise RuntimeError("simulated provider failure")


class MalformedResultProvider(RegistryRegulatoryProvider):
    async def verify(self, request):
        return RegulatoryVerificationResult(
            participant_type=request.participant_type,
            status=AnalysisStatus.SUCCESS,
            subject_name=request.subject_name,
            matched=True,
            explanation="Malformed test result without source evidence.",
        )


class RaisingRegistry(RegulatorySourceRegistry):
    def sources_for(self, *args, **kwargs):
        raise RuntimeError("simulated registry failure")


@pytest.mark.asyncio
async def test_provider_exception_returns_failed_without_match():
    provider = RaisingProvider()
    service = RegulatoryVerificationService(provider=provider)

    result = await service.verify(make_request())

    assert result.status == AnalysisStatus.FAILED
    assert result.matched is None
    assert result.evidence == []


@pytest.mark.asyncio
async def test_malformed_success_result_is_rejected():
    provider = MalformedResultProvider()
    service = RegulatoryVerificationService(provider=provider)

    result = await service.verify(make_request())

    assert result.status == AnalysisStatus.FAILED
    assert result.matched is None
    assert "failed validation" in result.explanation


@pytest.mark.asyncio
async def test_registry_exception_returns_failed_without_match():
    registry = RaisingRegistry()
    provider = RegistryRegulatoryProvider(registry)
    service = RegulatoryVerificationService(provider=provider)

    result = await service.verify(make_request())

    assert result.status == AnalysisStatus.FAILED
    assert result.matched is None


@pytest.mark.asyncio
async def test_unavailable_adapter_remains_unavailable():
    service = RegulatoryVerificationService()

    result = await service.verify(make_request())

    assert result.status == AnalysisStatus.UNAVAILABLE
    assert result.matched is None


@pytest.mark.asyncio
async def test_service_returns_structured_result_for_valid_request():
    service = RegulatoryVerificationService()

    result = await service.verify(make_request())

    assert isinstance(result, RegulatoryVerificationResult)
    assert result.participant_type == RegulatoryParticipantType.INVESTMENT_ADVISER
    assert result.status == AnalysisStatus.UNAVAILABLE
    assert result.matched is None

class UnavailableWithMatchProvider(RegistryRegulatoryProvider):
    async def verify(self, request):
        return RegulatoryVerificationResult(
            participant_type=request.participant_type,
            status=AnalysisStatus.UNAVAILABLE,
            matched=True,
            explanation="Invalid test result: unavailable but claims a match.",
        )


class SuccessWithoutEvidenceProvider(RegistryRegulatoryProvider):
    async def verify(self, request):
        source = self._registry.get_source("sebi_investment_advisers")
        return RegulatoryVerificationResult(
            participant_type=request.participant_type,
            status=AnalysisStatus.SUCCESS,
            subject_name=request.subject_name,
            source_id=source.source_id,
            source_url=source.url,
            matched=True,
            explanation="Invalid test result: no supporting evidence.",
        )


@pytest.mark.asyncio
async def test_unavailable_result_claiming_match_is_rejected():
    service = RegulatoryVerificationService(
        provider=UnavailableWithMatchProvider()
    )

    result = await service.verify(make_request())

    assert result.status == AnalysisStatus.FAILED
    assert result.matched is None
    assert "failed validation" in result.explanation


@pytest.mark.asyncio
async def test_success_without_evidence_is_rejected():
    service = RegulatoryVerificationService(
        provider=SuccessWithoutEvidenceProvider()
    )

    result = await service.verify(make_request())

    assert result.status == AnalysisStatus.FAILED
    assert result.matched is None
    assert "failed validation" in result.explanation
