"""Read-only lookup against locally stored SEBI directory snapshots.

This module reads local Excel files only. It does not make network requests
or claim that a match establishes current live SEBI registration.
"""

from __future__ import annotations

import logging
import re
from dataclasses import dataclass
from datetime import UTC, date, datetime
from pathlib import Path
from typing import Any

import xlrd

from app.contracts.regulatory import (
    RegulatoryParticipantType,
    RegulatorySource,
    RegulatoryVerificationRequest,
)
from app.contracts.status import AnalysisStatus
from app.core.config import settings

logger = logging.getLogger(__name__)

DATASET_AS_OF = date(2026, 10, 8)


@dataclass(frozen=True)
class DatasetDefinition:
    participant_type: RegulatoryParticipantType
    source_id: str
    source_name: str
    source_url: str
    path: str


@dataclass(frozen=True)
class DatasetRecord:
    name: str
    registration_number: str
    contact_person: str | None
    city: str | None
    state: str | None
    valid_from: str | None
    valid_to: str | None


def _normalize_registration(value: str | None) -> str:
    """Normalize spacing and case without removing meaningful punctuation."""
    if not value:
        return ""
    return re.sub(r"\s+", "", value).upper()


def _normalize_name(value: str | None) -> str:
    """Normalize case, punctuation, and whitespace for exact name comparison."""
    if not value:
        return ""

    value = value.casefold()
    value = re.sub(r"[^\w\s]", " ", value, flags=re.UNICODE)
    return " ".join(value.split())


def _cell_text(value: Any) -> str | None:
    """Convert a workbook cell to a trimmed string."""
    if value is None:
        return None

    text = str(value).strip()
    if not text or text.lower() in {"nan", "none"}:
        return None

    # Excel can expose integer-like identifiers as floats.
    if re.fullmatch(r"\d+\.0", text):
        text = text[:-2]

    return text


class SEBIDatasetLookup:
    """Perform conservative lookups against configured local snapshots."""

    def __init__(
        self,
        paths: dict[RegulatoryParticipantType, str] | None = None,
    ) -> None:
        configured_paths = paths or {
            RegulatoryParticipantType.INVESTMENT_ADVISER:
                settings.SEBI_INVESTMENT_ADVISER_DATASET_PATH,
            RegulatoryParticipantType.PORTFOLIO_MANAGER:
                settings.SEBI_PORTFOLIO_MANAGER_DATASET_PATH,
            RegulatoryParticipantType.RESEARCH_ANALYST:
                settings.SEBI_RESEARCH_ANALYST_DATASET_PATH,
        }

        self._definitions = {
            RegulatoryParticipantType.INVESTMENT_ADVISER: DatasetDefinition(
                participant_type=RegulatoryParticipantType.INVESTMENT_ADVISER,
                source_id="sebi_investment_adviser_dataset",
                source_name="SEBI Investment Adviser Directory Snapshot",
                source_url=(
                    "https://www.sebi.gov.in/sebiweb/other/"
                    "OtherAction.do?doRecognisedFpi=yes&intmId=13"
                ),
                path=configured_paths[
                    RegulatoryParticipantType.INVESTMENT_ADVISER
                ],
            ),
            RegulatoryParticipantType.PORTFOLIO_MANAGER: DatasetDefinition(
                participant_type=RegulatoryParticipantType.PORTFOLIO_MANAGER,
                source_id="sebi_portfolio_manager_dataset",
                source_name="SEBI Portfolio Manager Directory Snapshot",
                source_url="https://www.sebi.gov.in/sebiweb/other/OtherAction.do?doRecognisedFpi=yes&intmId=33",
                path=configured_paths[
                    RegulatoryParticipantType.PORTFOLIO_MANAGER
                ],
            ),
            RegulatoryParticipantType.RESEARCH_ANALYST: DatasetDefinition(
                participant_type=RegulatoryParticipantType.RESEARCH_ANALYST,
                source_id="sebi_research_analyst_dataset",
                source_name="SEBI Research Analyst Directory Snapshot",
                source_url=(
                    "https://www.sebi.gov.in/sebiweb/other/"
                    "OtherAction.do?doRecognisedFpi=yes&intmId=14"
                ),
                path=configured_paths[
                    RegulatoryParticipantType.RESEARCH_ANALYST
                ],
            ),
        }

    def source_definitions(self) -> list[RegulatorySource]:
        """Return source metadata for the configured local snapshots."""
        from app.contracts.regulatory import (
            RegulatoryCapability,
            RegulatorySourceKind,
        )

        return [
            RegulatorySource(
                source_id=definition.source_id,
                name=definition.source_name,
                authority="Securities and Exchange Board of India",
                url=definition.source_url,
                kind=RegulatorySourceKind.REGULATOR,
                participant_types=(definition.participant_type,),
                capabilities=(
                    RegulatoryCapability.REGISTRATION_LOOKUP,
                    RegulatoryCapability.REGISTRATION_STATUS,
                    RegulatoryCapability.IDENTITY_MATCH,
                ),
                # Local file reading is implemented, but this flag must not
                # be interpreted as evidence of live website connectivity.
                automated_access=False,
                notes=(
                    "Local directory snapshot dated 2026-10-08. "
                    "A snapshot match is not live registration verification."
                ),
            )
            for definition in self._definitions.values()
        ]

    @staticmethod
    def _find_header_row(sheet: Any) -> tuple[int, dict[str, int]]:
        """Find the header row by column names instead of fixed row number."""
        for row_index in range(min(sheet.nrows, 20)):
            headers = {
                _normalize_name(_cell_text(sheet.cell_value(row_index, col)))
                .replace(" ", ""): col
                for col in range(sheet.ncols)
            }

            if "name" in headers and "registrationno" in headers:
                return row_index, headers

        raise ValueError(
            "Could not find a header row containing Name and Registration No."
        )

    @staticmethod
    def _read_records(path: str) -> list[DatasetRecord]:
        """Read a directory workbook without modifying the source file."""
        workbook_path = Path(path)

        if not workbook_path.is_file():
            raise FileNotFoundError(
                f"Configured SEBI directory snapshot is unavailable: "
                f"{workbook_path.name}"
            )

        workbook = xlrd.open_workbook(str(workbook_path), on_demand=True)

        try:
            sheet = (
                workbook.sheet_by_name("Data")
                if "Data" in workbook.sheet_names()
                else workbook.sheet_by_index(0)
            )

            header_row, headers = SEBIDatasetLookup._find_header_row(sheet)

            def column(*names: str) -> int | None:
                for name in names:
                    index = headers.get(
                        _normalize_name(name).replace(" ", "")
                    )
                    if index is not None:
                        return index
                return None

            name_col = column("Name")
            registration_col = column("Registration No.")
            contact_col = column("Contact Person")
            city_col = column("City")
            state_col = column("State")
            from_col = column("From")
            to_col = column("To")

            if name_col is None or registration_col is None:
                raise ValueError("Required directory columns are missing.")

            records: list[DatasetRecord] = []

            for row_index in range(header_row + 1, sheet.nrows):
                row = sheet.row_values(row_index)

                def value(index: int | None) -> str | None:
                    if index is None or index >= len(row):
                        return None
                    return _cell_text(row[index])

                name = value(name_col)
                registration = value(registration_col)

                if not name or not registration:
                    continue

                records.append(
                    DatasetRecord(
                        name=name,
                        registration_number=registration,
                        contact_person=value(contact_col),
                        city=value(city_col),
                        state=value(state_col),
                        valid_from=value(from_col),
                        valid_to=value(to_col),
                    )
                )

            return records
        finally:
            workbook.release_resources()

    @staticmethod
    def _record_data(record: DatasetRecord) -> dict[str, Any]:
        return {
            "name": record.name,
            "registration_number": record.registration_number,
            "contact_person": record.contact_person,
            "city": record.city,
            "state": record.state,
            "source_reported_from": record.valid_from,
            "source_reported_to": record.valid_to,
            "dataset_as_of": DATASET_AS_OF.isoformat(),
            "match_method": None,
            "verification_scope": "local_directory_snapshot_only",
        }

    async def verify(
        self,
        request: RegulatoryVerificationRequest,
    ):
        """Match a request against its corresponding local snapshot."""
        from app.contracts.regulatory import (
            RegulatoryEvidenceItem,
            RegulatoryVerificationResult,
        )

        definition = self._definitions.get(request.participant_type)

        if definition is None:
            return None

        checked_at = datetime.now(UTC)

        def result(
            status: AnalysisStatus,
            explanation: str,
            limitations: list[str],
            *,
            matched: bool | None = None,
            record: DatasetRecord | None = None,
            match_method: str | None = None,
        ) -> RegulatoryVerificationResult:
            evidence = []

            if record is not None:
                data = self._record_data(record)
                data["match_method"] = match_method

                evidence.append(
                    RegulatoryEvidenceItem(
                        description=(
                            "Record matched in a local SEBI directory "
                            "snapshot dated 2026-10-08."
                        ),
                        source_id=definition.source_id,
                        source_url=definition.source_url,
                        retrieved_at=checked_at,
                        data=data,
                    )
                )

            return RegulatoryVerificationResult(
                participant_type=request.participant_type,
                status=status,
                subject_name=(
                    record.name if record else
                    request.subject_name or request.organization_name
                ),
                registration_number=(
                    record.registration_number if record else
                    request.registration_number
                ),
                source_id=definition.source_id,
                source_url=definition.source_url,
                checked_at=checked_at,
                matched=matched,
                registration_status=None,
                evidence=evidence,
                explanation=explanation,
                limitations=limitations + [
                    "This is a local snapshot lookup, not live SEBI verification.",
                    "Directory presence does not validate an offer or prove identity "
                    "of a person contacting the investigator.",
                    "Absence from this snapshot does not establish non-registration "
                    "or fraud.",
                ],
            )

        try:
            records = self._read_records(definition.path)
        except (OSError, ValueError, xlrd.XLRDError) as exc:
            logger.warning(
                "SEBI snapshot unavailable for %s: %s",
                request.participant_type.value,
                exc,
            )
            return result(
                AnalysisStatus.UNAVAILABLE,
                "The configured local SEBI directory snapshot could not be read.",
                ["No record-level verification was performed."],
            )

        if request.registration_number and request.registration_number.strip():
            target = _normalize_registration(request.registration_number)
            matches = [
                record for record in records
                if _normalize_registration(record.registration_number) == target
            ]
            match_method = "exact_registration_number"
        else:
            name = request.subject_name or request.organization_name
            target = _normalize_name(name)

            if not target:
                return result(
                    AnalysisStatus.INSUFFICIENT_EVIDENCE,
                    "A registration number or usable name is required for this lookup.",
                    ["No record-level verification was performed."],
                )

            matches = [
                record for record in records
                if _normalize_name(record.name) == target
            ]
            match_method = "exact_normalized_name"

        if not matches:
            return result(
                AnalysisStatus.NOT_VERIFIED,
                "No matching record was found in the local directory snapshot.",
                [
                    "No fuzzy matching was performed.",
                    "The directory may be incomplete or out of date.",
                ],
            )

        if len(matches) > 1:
            return result(
                AnalysisStatus.INSUFFICIENT_EVIDENCE,
                "Multiple directory records matched; the result is ambiguous.",
                [
                    "No record was selected.",
                    "Provide a registration number or additional identifiers.",
                ],
            )

        record = matches[0]

        return result(
            AnalysisStatus.SUCCESS,
            (
                "A matching record was found in the local SEBI directory "
                "snapshot. This result confirms a snapshot match only."
            ),
            [
                "Current registration status was not independently checked."
            ],
            matched=True,
            record=record,
            match_method=match_method,
        )
