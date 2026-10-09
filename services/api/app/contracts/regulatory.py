"""Contracts for VERA regulatory intelligence and verification."""

from __future__ import annotations

from datetime import datetime
from enum import StrEnum
from typing import Any

from pydantic import BaseModel, ConfigDict, Field, model_validator

from app.contracts.status import AnalysisStatus


class RegulatoryParticipantType(StrEnum):
    """Types of securities-market participants VERA can assess."""

    INVESTMENT_ADVISER = "investment_adviser"
    RESEARCH_ANALYST = "research_analyst"
    STOCKBROKER = "stockbroker"
    AUTHORISED_PERSON = "authorised_person"
    FINFLUENCER = "finfluencer"


class RegulatoryCapability(StrEnum):
    """Specific verification capabilities supported by a source."""

    REGISTRATION_LOOKUP = "registration_lookup"
    REGISTRATION_STATUS = "registration_status"
    IDENTITY_MATCH = "identity_match"
    BROKER_MEMBERSHIP_LOOKUP = "broker_membership_lookup"
    AUTHORISED_PERSON_LOOKUP = "authorised_person_lookup"
    DISCLOSURE_REVIEW = "disclosure_review"
    REGULATORY_GUIDANCE = "regulatory_guidance"


class RegulatorySourceKind(StrEnum):
    """Classification of a regulatory information source."""

    REGULATOR = "regulator"
    STOCK_EXCHANGE = "stock_exchange"
    OFFICIAL_GUIDANCE = "official_guidance"


class RegulatorySource(BaseModel):
    """Metadata describing an authoritative regulatory source."""

    model_config = ConfigDict(
        extra="forbid",
        frozen=True,
    )

    source_id: str = Field(min_length=1, max_length=100)
    name: str = Field(min_length=1, max_length=200)
    authority: str = Field(min_length=1, max_length=200)
    url: str = Field(min_length=1, max_length=2048)

    kind: RegulatorySourceKind

    participant_types: tuple[RegulatoryParticipantType, ...]
    capabilities: tuple[RegulatoryCapability, ...]

    enabled: bool = True

    # False means the registry does not claim that automated retrieval
    # has been implemented or validated for this source.
    automated_access: bool = False

    notes: str = ""

    @model_validator(mode="after")
    def validate_source(self) -> "RegulatorySource":
        if not self.url.startswith("https://"):
            raise ValueError("Regulatory source URLs must use HTTPS.")

        if not self.participant_types:
            raise ValueError(
                "A regulatory source must support at least one "
                "participant type."
            )

        if not self.capabilities:
            raise ValueError(
                "A regulatory source must declare at least one capability."
            )

        return self


class RegulatoryVerificationRequest(BaseModel):
    """Input for a future regulatory verification operation."""

    model_config = ConfigDict(extra="forbid")

    participant_type: RegulatoryParticipantType

    subject_name: str | None = Field(default=None, max_length=300)
    registration_number: str | None = Field(default=None, max_length=100)
    organization_name: str | None = Field(default=None, max_length=300)
    social_handle: str | None = Field(default=None, max_length=200)

    claimed_status: str | None = Field(default=None, max_length=100)

    # Additional identifiers supplied by the user, such as an exchange
    # membership number. These are inputs, not verified facts.
    identifiers: dict[str, str] = Field(default_factory=dict)

    @model_validator(mode="after")
    def require_identifier(self) -> "RegulatoryVerificationRequest":
        values = (
            self.subject_name,
            self.registration_number,
            self.organization_name,
            self.social_handle,
        )

        if not any(value and value.strip() for value in values):
            raise ValueError(
                "At least one subject identifier must be provided."
            )

        return self


class RegulatoryEvidenceItem(BaseModel):
    """A source-attributed item supporting a verification result."""

    model_config = ConfigDict(extra="forbid")

    description: str = Field(min_length=1, max_length=2000)

    source_id: str = Field(min_length=1, max_length=100)
    source_url: str = Field(min_length=1, max_length=2048)

    retrieved_at: datetime | None = None

    # Preserve relevant source content or structured fields.
    # This is evidence data, not an independent fraud determination.
    data: dict[str, Any] = Field(default_factory=dict)


class RegulatoryVerificationResult(BaseModel):
    """Structured result of a regulatory verification operation."""

    model_config = ConfigDict(extra="forbid")

    participant_type: RegulatoryParticipantType
    status: AnalysisStatus

    subject_name: str | None = None
    registration_number: str | None = None

    source_id: str | None = None
    source_url: str | None = None
    checked_at: datetime | None = None

    # True means the check established the stated match or condition.
    # False means it did not. None means the check could not determine it.
    matched: bool | None = None

    # This describes a source-reported registration state, when available.
    # It must not be inferred from the verification status.
    registration_status: str | None = None

    evidence: list[RegulatoryEvidenceItem] = Field(
        default_factory=list
    )

    explanation: str = Field(min_length=1, max_length=3000)
    limitations: list[str] = Field(default_factory=list)