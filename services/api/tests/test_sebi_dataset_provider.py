"""Tests for conservative matching against local SEBI snapshots."""

from pathlib import Path

import pytest

from app.contracts.regulatory import (
    RegulatoryParticipantType,
    RegulatoryVerificationRequest,
)
from app.contracts.status import AnalysisStatus
from app.providers.sebi_dataset_provider import (
    DatasetRecord,
    SEBIDatasetLookup,
)


PARTICIPANT = RegulatoryParticipantType.INVESTMENT_ADVISER

RECORDS = [
    DatasetRecord(
        name="Example Investment Advisers Pvt. Ltd.",
        registration_number="INA000000123",
        contact_person="A. Example",
        city="Mumbai",
        state="Maharashtra",
        valid_from="2020-01-01",
        valid_to="Perpetual",
    ),
    DatasetRecord(
        name="Northstar Advisory Services",
        registration_number="INA000000456",
        contact_person="B. Example",
        city="Pune",
        state="Maharashtra",
        valid_from="2021-01-01",
        valid_to="Perpetual",
    ),
]


def make_lookup(tmp_path: Path) -> SEBIDatasetLookup:
    """Build a lookup with isolated temporary paths."""
    paths = {
        RegulatoryParticipantType.INVESTMENT_ADVISER:
            str(tmp_path / "investment_adviser.xls"),
        RegulatoryParticipantType.PORTFOLIO_MANAGER:
            str(tmp_path / "portfolio_manager.xls"),
        RegulatoryParticipantType.RESEARCH_ANALYST:
            str(tmp_path / "research_analyst.xls"),
    }
    return SEBIDatasetLookup(paths=paths)


def make_request(
    *,
    subject_name: str | None = None,
    registration_number: str | None = None,
    participant_type: RegulatoryParticipantType = PARTICIPANT,
) -> RegulatoryVerificationRequest:
    return RegulatoryVerificationRequest(
        participant_type=participant_type,
        subject_name=subject_name,
        registration_number=registration_number,
    )


@pytest.mark.asyncio
async def test_exact_registration_number_match_returns_success(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
):
    lookup = make_lookup(tmp_path)
    monkeypatch.setattr(
        lookup,
        "_read_records",
        lambda path: RECORDS,
    )

    result = await lookup.verify(
        make_request(registration_number="INA000000123")
    )

    assert result is not None
    assert result.status == AnalysisStatus.SUCCESS
    assert result.matched is True
    assert result.registration_number == "INA000000123"
    assert result.source_id == "sebi_investment_adviser_dataset"
    assert len(result.evidence) == 1
    assert (
        result.evidence[0].data["match_method"]
        == "exact_registration_number"
    )
    assert (
        result.evidence[0].data["verification_scope"]
        == "local_directory_snapshot_only"
    )
    assert result.registration_status is None
    assert any("not live SEBI verification" in item for item in result.limitations)


@pytest.mark.asyncio
async def test_registration_number_matching_ignores_case_and_whitespace(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
):
    lookup = make_lookup(tmp_path)
    monkeypatch.setattr(
        lookup,
        "_read_records",
        lambda path: RECORDS,
    )

    result = await lookup.verify(
        make_request(registration_number="ina 000000123")
    )

    assert result is not None
    assert result.status == AnalysisStatus.SUCCESS
    assert result.matched is True
    assert result.evidence[0].data["match_method"] == "exact_registration_number"


@pytest.mark.asyncio
async def test_unique_normalized_name_match_returns_success(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
):
    lookup = make_lookup(tmp_path)
    monkeypatch.setattr(
        lookup,
        "_read_records",
        lambda path: RECORDS,
    )

    result = await lookup.verify(
        make_request(subject_name="  EXAMPLE Investment Advisers, Pvt. Ltd. ")
    )

    assert result is not None
    assert result.status == AnalysisStatus.SUCCESS
    assert result.matched is True
    assert result.subject_name == "Example Investment Advisers Pvt. Ltd."
    assert result.evidence[0].data["match_method"] == "exact_normalized_name"


@pytest.mark.asyncio
async def test_ambiguous_normalized_name_returns_insufficient_evidence(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
):
    lookup = make_lookup(tmp_path)
    ambiguous_records = [
        RECORDS[0],
        DatasetRecord(
            name="EXAMPLE INVESTMENT ADVISERS PVT LTD",
            registration_number="INA000000789",
            contact_person="C. Example",
            city="Delhi",
            state="Delhi",
            valid_from="2022-01-01",
            valid_to="Perpetual",
        ),
    ]
    monkeypatch.setattr(
        lookup,
        "_read_records",
        lambda path: ambiguous_records,
    )

    result = await lookup.verify(
        make_request(subject_name="Example Investment Advisers Pvt. Ltd.")
    )

    assert result is not None
    assert result.status == AnalysisStatus.INSUFFICIENT_EVIDENCE
    assert result.matched is None
    assert result.evidence == []
    assert any("No record was selected." in item for item in result.limitations)


@pytest.mark.asyncio
async def test_no_match_returns_not_verified_not_fraud(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
):
    lookup = make_lookup(tmp_path)
    monkeypatch.setattr(
        lookup,
        "_read_records",
        lambda path: RECORDS,
    )

    result = await lookup.verify(
        make_request(registration_number="INA999999999")
    )

    assert result is not None
    assert result.status == AnalysisStatus.NOT_VERIFIED
    assert result.matched is None
    assert result.evidence == []
    assert any(
        "does not establish non-registration or fraud" in item
        for item in result.limitations
    )


@pytest.mark.asyncio
async def test_missing_workbook_returns_unavailable(
    tmp_path: Path,
):
    lookup = make_lookup(tmp_path)

    result = await lookup.verify(
        make_request(subject_name="Example Adviser")
    )

    assert result is not None
    assert result.status == AnalysisStatus.UNAVAILABLE
    assert result.matched is None
    assert result.evidence == []
    assert any(
        "record-level verification" in item.lower()
        for item in result.limitations
    )


@pytest.mark.asyncio
async def test_unsupported_participant_returns_none(
    tmp_path: Path,
):
    lookup = make_lookup(tmp_path)

    result = await lookup.verify(
        make_request(
            subject_name="Example Finfluencer",
            participant_type=RegulatoryParticipantType.FINFLUENCER,
        )
    )

    assert result is None


@pytest.mark.asyncio
async def test_registration_number_takes_precedence_over_name(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
):
    lookup = make_lookup(tmp_path)
    monkeypatch.setattr(
        lookup,
        "_read_records",
        lambda path: RECORDS,
    )

    # The name matches a known record, but the supplied registration number
    # does not. The reader must not fall back to matching by name.
    result = await lookup.verify(
        make_request(
            subject_name="Example Investment Advisers Pvt. Ltd.",
            registration_number="INA999999999",
        )
    )

    assert result is not None
    assert result.status == AnalysisStatus.NOT_VERIFIED
    assert result.matched is None
    assert result.evidence == []
