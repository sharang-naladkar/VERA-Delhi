"""Tests for regulatory request and result validation."""

from datetime import UTC, datetime

from app.contracts.regulatory import (
    RegulatoryEvidenceItem,
    RegulatoryParticipantType,
    RegulatoryVerificationRequest,
    RegulatoryVerificationResult,
)
from app.contracts.status import AnalysisStatus
from app.providers.regulatory_result_validator import RegulatoryResultValidator
from app.providers.regulatory_source_registry import RegulatorySourceRegistry


def setup_validator():
    registry = RegulatorySourceRegistry()
    validator = RegulatoryResultValidator(registry)
    source = registry.get_source("sebi_investment_advisers")
    assert source is not None
    return validator, source


def make_request():
    return RegulatoryVerificationRequest(
        participant_type=RegulatoryParticipantType.INVESTMENT_ADVISER,
        subject_name="Example Adviser",
        registration_number="INA000000001",
    )


def make_success_result(source):
    now = datetime.now(UTC)
    return RegulatoryVerificationResult(
        participant_type=RegulatoryParticipantType.INVESTMENT_ADVISER,
        status=AnalysisStatus.SUCCESS,
        subject_name="Example Adviser",
        registration_number="INA000000001",
        source_id=source.source_id,
        source_url=source.url,
        checked_at=now,
        matched=True,
        registration_status="active",
        evidence=[
            RegulatoryEvidenceItem(
                description="Example retrieved record",
                source_id=source.source_id,
                source_url=source.url,
                retrieved_at=now,
                data={"record_reference": "test-fixture"},
            )
        ],
        explanation="Test fixture only; not a real regulatory lookup.",
    )


def test_valid_request_has_no_validation_errors():
    validator, _ = setup_validator()

    assert validator.validate_request(make_request()) == []


def test_valid_structured_success_result_passes_validation():
    validator, source = setup_validator()

    errors = validator.validate_result(
        make_request(),
        make_success_result(source),
    )

    assert errors == []


def test_success_without_evidence_is_rejected():
    validator, source = setup_validator()
    result = make_success_result(source).model_copy(update={"evidence": []})

    errors = validator.validate_result(make_request(), result)

    assert any("requires source-attributed evidence" in error for error in errors)


def test_success_without_match_outcome_is_rejected():
    validator, source = setup_validator()
    result = make_success_result(source).model_copy(update={"matched": None})

    errors = validator.validate_result(make_request(), result)

    assert any("specify the match outcome" in error for error in errors)


def test_unregistered_source_is_rejected():
    validator, _ = setup_validator()
    result = make_success_result(
        setup_validator()[1]
    ).model_copy(update={"source_id": "unknown_source"})

    errors = validator.validate_result(make_request(), result)

    assert any("unregistered source" in error for error in errors)


def test_contradictory_registration_number_is_rejected():
    validator, source = setup_validator()
    result = make_success_result(source).model_copy(
        update={"registration_number": "INA999999999"}
    )

    errors = validator.validate_result(make_request(), result)

    assert any("contradicts the request" in error for error in errors)


def test_unavailable_result_must_not_claim_match():
    validator, source = setup_validator()
    result = RegulatoryVerificationResult(
        participant_type=RegulatoryParticipantType.INVESTMENT_ADVISER,
        status=AnalysisStatus.UNAVAILABLE,
        source_id=source.source_id,
        source_url=source.url,
        matched=True,
        explanation="Test fixture.",
    )

    errors = validator.validate_result(make_request(), result)

    assert any("Non-conclusive result" in error for error in errors)


def test_wrong_participant_type_is_rejected():
    validator, source = setup_validator()
    result = make_success_result(source).model_copy(
        update={"participant_type": RegulatoryParticipantType.STOCKBROKER}
    )

    errors = validator.validate_result(make_request(), result)

    assert any("participant type does not match" in error for error in errors)


def test_evidence_without_retrieval_timestamp_is_rejected():
    validator, source = setup_validator()
    result = make_success_result(source).model_copy(
        update={
            "evidence": [
                RegulatoryEvidenceItem(
                    description="Missing timestamp",
                    source_id=source.source_id,
                    source_url=source.url,
                )
            ]
        }
    )

    errors = validator.validate_result(make_request(), result)

    assert any("retrieval timestamp" in error for error in errors)
