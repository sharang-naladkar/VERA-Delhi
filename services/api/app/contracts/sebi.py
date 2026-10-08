"""Contracts for SEBI regulatory intelligence and entity verification."""

from datetime import UTC, datetime
from enum import StrEnum
from typing import Any
from uuid import UUID, uuid4

from pydantic import BaseModel, Field


class VerificationStatus(StrEnum):
    """Semantic result of an authoritative regulatory verification."""

    VERIFIED = "VERIFIED"
    NOT_VERIFIED = "NOT_VERIFIED"
    PARTIAL = "PARTIAL"
    FAILED = "FAILED"
    UNAVAILABLE = "UNAVAILABLE"
    INSUFFICIENT_EVIDENCE = "INSUFFICIENT_EVIDENCE"


class RegulatorySource(BaseModel):
    """Provenance for an authoritative regulatory source."""

    name: str = Field(..., min_length=1)
    url: str | None = None
    document_title: str | None = None
    document_reference: str | None = None
    section: str | None = None
    page: int | None = Field(default=None, ge=1)
    retrieved_at: datetime = Field(default_factory=lambda: datetime.now(UTC))


class RegulatoryClaim(BaseModel):
    """A regulatory claim supported by a source."""

    claim: str = Field(..., min_length=1)
    source: RegulatorySource
    evidence_text: str | None = None


class VerificationResult(BaseModel):
    """Typed result of verifying a regulated entity."""

    id: UUID = Field(default_factory=uuid4)
    status: VerificationStatus
    entity_name: str | None = None
    registration_number: str | None = None
    entity_type: str | None = None
    claimed_organization: str | None = None
    matched_name: str | None = None
    matched_registration_number: str | None = None
    source: RegulatorySource | None = None
    claims: list[RegulatoryClaim] = Field(default_factory=list)
    details: str | None = None
    metadata: dict[str, Any] = Field(default_factory=dict)