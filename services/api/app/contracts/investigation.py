"""Investigation Request and Response Data Contracts."""

from datetime import datetime
from typing import Any
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field

from app.contracts.regulatory import RegulatoryVerificationRequest


class CreateInvestigationRequest(BaseModel):
    """Payload to initiate a new investigation."""

    title: str | None = Field(
        None,
        max_length=255,
        description="Optional brief title",
    )
    description: str | None = Field(
        None,
        description="Optional description of suspicious activity",
    )
    text: str | None = Field(
        None,
        description="Suspicious text, message, or claim to investigate",
    )
    input_type: str = Field(
        default="text",
        description=(
            "Input modality (e.g. text, message, claim, profile_description)"
        ),
    )
    metadata: dict[str, Any] = Field(
        default_factory=dict,
        description="Initial context metadata",
    )
    regulatory_verification_request: (
        RegulatoryVerificationRequest | None
    ) = Field(
        default=None,
        description=(
            "Optional explicit request to check a securities-market "
            "participant against registered regulatory sources."
        ),
    )


class InvestigationResponse(BaseModel):
    """Standardized representation of an investigation record."""

    model_config = ConfigDict(from_attributes=True)

    id: UUID
    title: str | None = None
    description: str | None = None
    status: str
    vera_version: str
    created_at: datetime
    updated_at: datetime

    evidence_count: int = Field(
        default=0,
        description="Total forensic evidence items collected",
    )
    evidence: list[dict[str, Any]] = Field(
        default_factory=list,
        description="Collected forensic evidence contracts",
    )
    result_summary: str | None = Field(
        None,
        description="Objective investigator summary of findings",
    )
    state: dict[str, Any] | None = Field(
        None,
        description="Serialized investigation state",
    )

    risk_assessment: dict[str, Any] | None = Field(
        None,
        description=(
            "Deterministic, uncalibrated indicator score and contributing "
            "evidence; not a probability of fraud."
        ),
    )
    investigation_report: dict[str, Any] | None = Field(
        None,
        description="Structured report grounded in collected evidence",
    )