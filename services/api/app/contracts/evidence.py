"""Common Evidence Contract for VERA."""

from datetime import UTC, datetime
from typing import Any
from uuid import UUID, uuid4

from pydantic import BaseModel, ConfigDict, Field

from app.contracts.status import AnalysisStatus, EvidenceType, SeverityLevel


class EvidenceContract(BaseModel):
    """Standardized multi-modal evidence item produced by all analyzers and pipelines."""

    model_config = ConfigDict(from_attributes=True)

    id: UUID = Field(default_factory=uuid4, description="Unique UUID for this evidence record")
    investigation_id: UUID = Field(..., description="Target investigation UUID")
    input_id: UUID | None = Field(None, description="Source input asset UUID if applicable")
    type: EvidenceType = Field(..., description="Type/domain of evidence")
    category: str = Field(..., description="Domain-specific tag or category")
    severity: SeverityLevel = Field(default=SeverityLevel.LOW, description="Assessed risk severity level")
    confidence: float = Field(default=0.0, ge=0.0, le=1.0, description="Confidence score between 0.0 and 1.0")
    description: str = Field(..., description="Human-readable and structured summary of finding")
    source_type: str = Field(default="model", description="Origin category (model, heuristic, database, human)")
    source_name: str = Field(..., description="Specific provider or analyzer name (e.g. ocr_tesseract, mesonet)")
    source_version: str | None = Field(None, description="Version string of analyzer or model used")
    status: AnalysisStatus = Field(default=AnalysisStatus.SUCCESS, description="Execution outcome of analyzer")
    raw_payload: dict[str, Any] | None = Field(default=None, description="Detailed JSON output from provider")
    metadata: dict[str, Any] = Field(default_factory=dict, description="Arbitrary supplemental metadata")
    created_at: datetime = Field(
        default_factory=lambda: datetime.now(UTC),
        description="UTC creation timestamp",
    )
