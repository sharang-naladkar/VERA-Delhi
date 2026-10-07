"""Tool Registry for VERA Investigator."""

from typing import Any

from app.investigator.tools.base import InvestigationTool
from app.investigator.tools.claim_extractor import ClaimExtractorTool
from app.investigator.tools.entity_extractor import EntityExtractorTool
from app.investigator.tools.normalizer import InputNormalizerTool
from app.investigator.tools.pattern_analyzer import ScamPatternAnalyzerTool
from app.providers.llm import LLMProvider


class ToolRegistry:
    """Registry maintaining available investigative tools for the VERA investigator."""

    def __init__(self) -> None:
        self._tools: dict[str, InvestigationTool] = {}

    def register(self, tool: InvestigationTool) -> None:
        """Registers a tool instance."""
        self._tools[tool.name] = tool

    def get(self, name: str) -> InvestigationTool | None:
        """Retrieves a tool by its unique name."""
        return self._tools.get(name)

    def list_tools(self) -> list[InvestigationTool]:
        """Returns all registered tool instances."""
        return list(self._tools.values())

    def list_names(self) -> list[str]:
        """Returns registered tool names."""
        return list(self._tools.keys())


def create_default_registry(llm_provider: LLMProvider) -> ToolRegistry:
    """Creates registry initialized with Phase 02 initial tools."""
    registry = ToolRegistry()
    registry.register(InputNormalizerTool())
    registry.register(EntityExtractorTool(llm_provider=llm_provider))
    registry.register(ClaimExtractorTool(llm_provider=llm_provider))
    registry.register(ScamPatternAnalyzerTool(llm_provider=llm_provider))
    return registry
