"""Investigation tools package."""

from app.investigator.tools.audio_tool import AudioTranscriptionTool
from app.investigator.tools.base import InvestigationTool, ToolResult
from app.investigator.tools.claim_extractor import ClaimExtractorTool
from app.investigator.tools.deepfake_tool import DeepfakeDetectionTool
from app.investigator.tools.entity_extractor import EntityExtractorTool
from app.investigator.tools.face_tool import FaceDetectionTool
from app.investigator.tools.normalizer import InputNormalizerTool
from app.investigator.tools.ocr_tool import OCRTool
from app.investigator.tools.pattern_analyzer import ScamPatternAnalyzerTool
from app.investigator.tools.registry import ToolRegistry, create_default_registry
from app.investigator.tools.video_tool import VideoAnalysisTool

__all__ = [
    "InvestigationTool",
    "ToolResult",
    "InputNormalizerTool",
    "EntityExtractorTool",
    "ClaimExtractorTool",
    "ScamPatternAnalyzerTool",
    "OCRTool",
    "AudioTranscriptionTool",
    "VideoAnalysisTool",
    "FaceDetectionTool",
    "DeepfakeDetectionTool",
    "ToolRegistry",
    "create_default_registry",
]
