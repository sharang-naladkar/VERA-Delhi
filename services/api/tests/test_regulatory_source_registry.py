import pytest
from pydantic import ValidationError

from app.contracts.regulatory import (
    RegulatoryCapability,
    RegulatoryParticipantType,
    RegulatorySource,
    RegulatorySourceKind,
    RegulatoryVerificationRequest,
    RegulatoryVerificationResult,
)
from app.contracts.status import AnalysisStatus
from app.providers.regulatory_source_registry import (
    RegulatorySourceRegistry,
)


def test_registry_contains_authoritative_sources():
    registry = RegulatorySourceRegistry()

    sources = registry.list_sources()

    assert len(sources) == 6

    source_ids = {source.source_id for source in sources}

    assert "sebi_investment_advisers" in source_ids
    assert "sebi_research_analysts" in source_ids
    assert "nse_broker_locator" in source_ids
    assert "bse_member_directory" in source_ids


def test_get_source_returns_registered_source():
    registry = RegulatorySourceRegistry()

    source = registry.get_source("sebi_investment_advisers")

    assert source is not None
    assert source.authority == "Securities and Exchange Board of India"
    assert (
        RegulatoryParticipantType.INVESTMENT_ADVISER
        in source.participant_types
    )


def test_get_source_returns_none_for_unknown_source():
    registry = RegulatorySourceRegistry()

    assert registry.get_source("unknown_source") is None


def test_sources_for_investment_adviser():
    registry = RegulatorySourceRegistry()

    sources = registry.sources_for(
        RegulatoryParticipantType.INVESTMENT_ADVISER
    )

    source_ids = {source.source_id for source in sources}

    assert "sebi_investment_advisers" in source_ids
    assert "bse_enlisted_investment_advisers" in source_ids

    assert "sebi_research_analysts" not in source_ids


def test_sources_for_broker_membership_capability():
    registry = RegulatorySourceRegistry()

    sources = registry.sources_for(
        RegulatoryParticipantType.STOCKBROKER,
        capability=(
            RegulatoryCapability.BROKER_MEMBERSHIP_LOOKUP
        ),
    )

    source_ids = {source.source_id for source in sources}

    assert source_ids == {
        "bse_member_directory",
        "nse_broker_locator",
    }


def test_sources_for_finfluencer_has_no_assumed_registry():
    registry = RegulatorySourceRegistry()

    sources = registry.sources_for(
        RegulatoryParticipantType.FINFLUENCER
    )

    assert sources == []


def test_disabled_sources_are_excluded_by_default():
    source = RegulatorySource(
        source_id="test_source",
        name="Test Source",
        authority="Test Authority",
        url="https://example.com/registry",
        kind=RegulatorySourceKind.REGULATOR,
        participant_types=(
            RegulatoryParticipantType.INVESTMENT_ADVISER,
        ),
        capabilities=(
            RegulatoryCapability.REGISTRATION_LOOKUP,
        ),
        enabled=False,
    )

    registry = RegulatorySourceRegistry(sources=[source])

    assert registry.list_sources() == []
    assert len(registry.list_sources(enabled_only=False)) == 1

    assert (
        registry.sources_for(
            RegulatoryParticipantType.INVESTMENT_ADVISER
        )
        == []
    )


def test_duplicate_source_ids_are_rejected():
    source = RegulatorySource(
        source_id="duplicate",
        name="Test Source",
        authority="Test Authority",
        url="https://example.com/registry",
        kind=RegulatorySourceKind.REGULATOR,
        participant_types=(
            RegulatoryParticipantType.INVESTMENT_ADVISER,
        ),
        capabilities=(
            RegulatoryCapability.REGISTRATION_LOOKUP,
        ),
    )

    with pytest.raises(ValueError, match="Duplicate"):
        RegulatorySourceRegistry(sources=[source, source])


def test_source_requires_https():
    with pytest.raises(ValidationError):
        RegulatorySource(
            source_id="insecure",
            name="Insecure Source",
            authority="Test Authority",
            url="http://example.com/registry",
            kind=RegulatorySourceKind.REGULATOR,
            participant_types=(
                RegulatoryParticipantType.INVESTMENT_ADVISER,
            ),
            capabilities=(
                RegulatoryCapability.REGISTRATION_LOOKUP,
            ),
        )


def test_verification_request_requires_an_identifier():
    with pytest.raises(ValidationError):
        RegulatoryVerificationRequest(
            participant_type=(
                RegulatoryParticipantType.INVESTMENT_ADVISER
            ),
        )


def test_verification_request_accepts_registration_number():
    request = RegulatoryVerificationRequest(
        participant_type=(
            RegulatoryParticipantType.INVESTMENT_ADVISER
        ),
        registration_number="INA000017523",
    )

    assert request.registration_number == "INA000017523"


def test_unavailable_result_does_not_claim_a_match():
    result = RegulatoryVerificationResult(
        participant_type=(
            RegulatoryParticipantType.INVESTMENT_ADVISER
        ),
        status=AnalysisStatus.UNAVAILABLE,
        subject_name="Example Adviser",
        matched=None,
        registration_status=None,
        explanation=(
            "The authoritative source was unavailable. "
            "No registration conclusion could be reached."
        ),
        limitations=[
            "No live source lookup was completed."
        ],
    )

    assert result.status == AnalysisStatus.UNAVAILABLE
    assert result.matched is None
    assert result.registration_status is None
    assert result.evidence == []


def test_not_verified_is_not_the_same_as_fraud():
    result = RegulatoryVerificationResult(
        participant_type=(
            RegulatoryParticipantType.RESEARCH_ANALYST
        ),
        status=AnalysisStatus.NOT_VERIFIED,
        subject_name="Example Analyst",
        matched=False,
        explanation=(
            "The submitted identity was not verified against "
            "the selected source."
        ),
        limitations=[
            "A failed match does not establish fraudulent conduct."
        ],
    )

    assert result.status == AnalysisStatus.NOT_VERIFIED
    assert result.matched is False
    assert "fraudulent conduct" in result.limitations[0]