"""Tests for the regulatory verification provider interface."""

import pytest

from app.contracts.regulatory import (
    RegulatoryParticipantType,
    RegulatoryVerificationRequest,
    RegulatoryVerificationResult,
)
from app.contracts.status import AnalysisStatus
from app.providers.regulatory_verification import (
    RegulatoryVerificationProvider,
)


class ExampleRegulatoryProvider(RegulatoryVerificationProvider):
    @property
    def provider_name(self) -> str:
        return "example_regulatory"

    @property
    def is_available(self) -> bool:
        return True

    async def health_check(self) -> dict:
        return {"status": "available"}

    @property
    def supported_source_ids(self) -> tuple[str, ...]:
        return ("example_source",)

    async def verify(
        self,
        request: RegulatoryVerificationRequest,
    ) -> RegulatoryVerificationResult:
        return RegulatoryVerificationResult(
            participant_type=request.participant_type,
            status=AnalysisStatus.UNAVAILABLE,
            subject_name=request.subject_name,
            registration_number=request.registration_number,
            source_id="example_source",
            matched=None,
            explanation="Example provider does not perform live verification.",
            limitations=["No authoritative source was queried."],
        )


def test_regulatory_provider_exposes_supported_sources():
    provider = ExampleRegulatoryProvider()

    assert provider.provider_name == "example_regulatory"
    assert provider.supported_source_ids == ("example_source",)


@pytest.mark.asyncio
async def test_regulatory_provider_returns_contract_result():
    provider = ExampleRegulatoryProvider()
    request = RegulatoryVerificationRequest(
        participant_type=RegulatoryParticipantType.INVESTMENT_ADVISER,
        subject_name="Example Adviser",
    )

    result = await provider.verify(request)

    assert result.status == AnalysisStatus.UNAVAILABLE
    assert result.matched is None
    assert result.source_id == "example_source"
    assert result.evidence == []
