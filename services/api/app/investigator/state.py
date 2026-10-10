"""Typed LangGraph Investigation State for VERA."""

from datetime import UTC, datetime
from typing import Any, TypedDict
from uuid import UUID, uuid4

from pydantic import BaseModel, Field

from app.contracts.evidence import EvidenceContract
from app.contracts.status import AnalysisStatus
from app.investigator.schemas import (
    ClaimExtraction,
    EntityExtraction,
    InvestigationPlan,
    ScamPatternAnalysis,
)


class ToolExecutionRecord(BaseModel):
    """Log record of a specialized tool execution."""

    tool_name: str
    tool_version: str
    status: AnalysisStatus
    duration_ms: float
    evidence_count: int
    error: str | None = None
    output_summary: str | None = None


class InvestigationStateDict(TypedDict, total=False):
    """TypedDict definition for LangGraph state graph."""

    investigation_id: str
    input_id: str | None
    input_type: str
    regulatory_verification_request: dict[str, Any] | None
    raw_input_reference: str | None
    raw_input_text: str
    normalized_input: str
    image_bytes: bytes | None
    audio_bytes: bytes | None
    video_bytes: bytes | None
    media_bytes: bytes | None
    entities: list[dict[str, Any]]
    claims: list[dict[str, Any]]
    indicators: list[str]
    investigation_plan: dict[str, Any] | None
    scam_pattern_analysis: dict[str, Any] | None
    evidence: list[dict[str, Any]]
    tool_results: list[dict[str, Any]]
    risk_assessment: dict[str, Any] | None
    investigation_report: dict[str, Any] | None
    messages: list[dict[str, str]]
    current_step: str
    status: str
    errors: list[str]
    warnings: list[str]
    llm_metadata: dict[str, Any]
    timestamps: dict[str, str]


class InvestigationState(BaseModel):
    """Pydantic model representing complete, validated investigation state."""

    investigation_id: UUID = Field(default_factory=uuid4)
    input_id: UUID | None = None
    input_type: str = "text"
    regulatory_verification_request: dict[str, Any] | None = None
    raw_input_reference: str | None = None
    raw_input_text: str = ""
    normalized_input: str = ""
    entities: list[dict[str, Any]] = Field(default_factory=list)
    claims: list[dict[str, Any]] = Field(default_factory=list)
    indicators: list[str] = Field(default_factory=list)
    investigation_plan: dict[str, Any] | None = None
    scam_pattern_analysis: dict[str, Any] | None = None
    evidence: list[dict[str, Any]] = Field(default_factory=list)
    tool_results: list[dict[str, Any]] = Field(default_factory=list)

    # Deterministic risk assessment and structured investigation report.
    risk_assessment: dict[str, Any] | None = None
    investigation_report: dict[str, Any] | None = None

    messages: list[dict[str, str]] = Field(default_factory=list)
    current_step: str = "initialized"
    status: AnalysisStatus = AnalysisStatus.PENDING
    errors: list[str] = Field(default_factory=list)
    warnings: list[str] = Field(default_factory=list)
    llm_metadata: dict[str, Any] = Field(default_factory=dict)
    timestamps: dict[str, str] = Field(
        default_factory=lambda: {
            "initialized_at": datetime.now(UTC).isoformat()
        }
    )

    def to_graph_state(self) -> InvestigationStateDict:
        """Serializes Pydantic state to a LangGraph-compatible dictionary."""

        return {
            "investigation_id": str(self.investigation_id),
            "input_id": str(self.input_id) if self.input_id else None,
            "input_type": self.input_type,
            "regulatory_verification_request": (
                self.regulatory_verification_request
            ),
            "raw_input_reference": self.raw_input_reference,
            "raw_input_text": self.raw_input_text,
            "normalized_input": self.normalized_input,
            "entities": self.entities,
            "claims": self.claims,
            "indicators": self.indicators,
            "investigation_plan": self.investigation_plan,
            "scam_pattern_analysis": self.scam_pattern_analysis,
            "evidence": self.evidence,
            "tool_results": self.tool_results,
            "risk_assessment": self.risk_assessment,
            "investigation_report": self.investigation_report,
            "messages": self.messages,
            "current_step": self.current_step,
            "status": self.status.value,
            "errors": self.errors,
            "warnings": self.warnings,
            "llm_metadata": self.llm_metadata,
            "timestamps": self.timestamps,
        }

    @classmethod
    def from_graph_state(
        cls,
        state_dict: InvestigationStateDict,
    ) -> "InvestigationState":
        """Instantiates and validates InvestigationState from graph state."""

        status_val = state_dict.get(
            "status",
            AnalysisStatus.PENDING.value,
        )

        try:
            status = AnalysisStatus(status_val)
        except ValueError:
            status = AnalysisStatus.PENDING

        return cls(
            investigation_id=UUID(state_dict["investigation_id"]),
            input_id=(
                UUID(state_dict["input_id"])
                if state_dict.get("input_id")
                else None
            ),
            input_type=state_dict.get("input_type", "text"),
            regulatory_verification_request=state_dict.get(
                "regulatory_verification_request"
            ),
            raw_input_reference=state_dict.get("raw_input_reference"),
            raw_input_text=state_dict.get("raw_input_text", ""),
            normalized_input=state_dict.get("normalized_input", ""),
            entities=state_dict.get("entities", []),
            claims=state_dict.get("claims", []),
            indicators=state_dict.get("indicators", []),
            investigation_plan=state_dict.get("investigation_plan"),
            scam_pattern_analysis=state_dict.get("scam_pattern_analysis"),
            evidence=state_dict.get("evidence", []),
            tool_results=state_dict.get("tool_results", []),
            risk_assessment=state_dict.get("risk_assessment"),
            investigation_report=state_dict.get("investigation_report"),
            messages=state_dict.get("messages", []),
            current_step=state_dict.get("current_step", "unknown"),
            status=status,
            errors=state_dict.get("errors", []),
            warnings=state_dict.get("warnings", []),
            llm_metadata=state_dict.get("llm_metadata", {}),
            timestamps=state_dict.get("timestamps", {}),
        )

    def add_evidence(self, item: EvidenceContract) -> None:
        """Appends a validated evidence contract to the state."""

        self.evidence.append(item.model_dump(mode="json"))

    def add_error(self, error: str) -> None:
        """Records an error and updates status fail-safe."""

        self.errors.append(error)

        if self.status != AnalysisStatus.FAILED:
            self.status = AnalysisStatus.PARTIAL