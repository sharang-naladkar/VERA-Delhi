"""Investigation tools package."""

from app.investigator.tools.base import InvestigationTool, ToolResult
from app.investigator.tools.claim_extractor import ClaimExtractorTool
from app.investigator.tools.entity_extractor import EntityExtractorTool
from app.investigator.tools.normalizer import InputNormalizerTool
from app.investigator.tools.pattern_analyzer import ScamPatternAnalyzerTool
from app.investigator.tools.registry import ToolRegistry, create_default_registry

__all__ = [
    "InvestigationTool",
    "ToolResult",
    "InputNormalizerTool",
    "EntityExtractorTool",
    "ClaimExtractorTool",
    "ScamPatternAnalyzerTool",
    "ToolRegistry",
    "create_default_registry",
]
