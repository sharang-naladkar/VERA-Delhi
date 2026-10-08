"""Deterministic evidence correlation contracts for VERA."""

from typing import Any
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field

from app.contracts.evidence import EvidenceContract
from app.investigator.tools.base import ToolResult


class CorrelatedEntity(BaseModel):
    """Entity candidate linked into the evidence chain."""

    model_config = ConfigDict(extra="forbid")

    id: str = Field(..., min_length=1)
    entity_type: str = Field(..., min_length=1)
    name: str = Field(..., min_length=1)
    normalized_value: str = Field(..., min_length=1)
    source_text: str = ""
    confidence: float = Field(..., ge=0.0, le=1.0)


class CorrelatedClaim(BaseModel):
    """Claim candidate linked into the evidence chain."""

    model_config = ConfigDict(extra="forbid")

    id: str = Field(..., min_length=1)
    claim_type: str = Field(..., min_length=1)
    claim: str = Field(..., min_length=1)
    source_text: str = ""
    confidence: float = Field(..., ge=0.0, le=1.0)


class CorrelatedIndicator(BaseModel):
    """Deterministic identifier for an investigation indicator."""

    model_config = ConfigDict(extra="forbid")

    id: str = Field(..., min_length=1)
    value: str = Field(..., min_length=1)


class EvidenceCorrelation(BaseModel):
    """Complete deterministic correlation view for one investigation."""

    model_config = ConfigDict(extra="forbid")

    investigation_id: UUID
    input_id: UUID | None = None
    input_reference: str | None = None
    entities: list[CorrelatedEntity] = Field(default_factory=list)
    claims: list[CorrelatedClaim] = Field(default_factory=list)
    indicators: list[CorrelatedIndicator] = Field(default_factory=list)
    tool_results: list[ToolResult] = Field(default_factory=list)
    evidence: list[EvidenceContract] = Field(default_factory=list)
    metadata: dict[str, Any] = Field(default_factory=dict)
