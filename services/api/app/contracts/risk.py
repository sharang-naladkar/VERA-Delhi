"""Deterministic risk assessment contracts for VERA."""

from enum import StrEnum
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field

from app.contracts.status import AnalysisStatus


class RiskLevel(StrEnum):
    """Deterministic risk classification derived from the 0-100 risk index."""

    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


class RiskSignal(BaseModel):
    """One deterministic risk contribution derived from structured evidence."""

    model_config = ConfigDict(extra="forbid")

    id: str = Field(..., min_length=1)
    category: str = Field(..., min_length=1)
    description: str = Field(..., min_length=1)
    points: int = Field(..., ge=0)
    source: str = Field(..., min_length=1)
    evidence_ids: list[UUID] = Field(default_factory=list)


class RiskAssessment(BaseModel):
    """Final deterministic risk assessment for an investigation."""

    model_config = ConfigDict(extra="forbid")

    investigation_id: UUID
    score: int = Field(
        ...,
        ge=0,
        le=100,
        description="Deterministic risk index from 0 to 100. This is not a fraud probability.",
    )
    level: RiskLevel
    status: AnalysisStatus
    signals: list[RiskSignal] = Field(default_factory=list)
    uncertainties: list[str] = Field(default_factory=list)
