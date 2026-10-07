"""Base Abstraction for VERA Investigation Tools."""

from abc import ABC, abstractmethod
from typing import Any

from pydantic import BaseModel, Field

from app.contracts.evidence import EvidenceContract
from app.contracts.status import AnalysisStatus


class ToolResult(BaseModel):
    """Standardized output produced by all investigation tools."""

    tool_name: str
    tool_version: str
    status: AnalysisStatus
    evidence: list[EvidenceContract] = Field(default_factory=list)
    output_data: dict[str, Any] = Field(default_factory=dict)
    error_message: str | None = None
    duration_ms: float = 0.0


class InvestigationTool(ABC):
    """Abstract interface for all specialized investigative tools."""

    @property
    @abstractmethod
    def name(self) -> str:
        """Unique, stable tool identifier."""
        pass

    @property
    @abstractmethod
    def description(self) -> str:
        """Purpose and capabilities of the tool."""
        pass

    @property
    @abstractmethod
    def version(self) -> str:
        """Version string of the tool implementation."""
        pass

    @abstractmethod
    async def execute(self, state: dict[str, Any]) -> ToolResult:
        """
        Executes the tool logic on the current state.
        Must handle errors gracefully and never raise unhandled exceptions.
        """
        pass
