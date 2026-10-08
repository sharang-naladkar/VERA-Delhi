"""Tool Registry for VERA Investigator."""

from app.investigator.tools.audio_tool import AudioTranscriptionTool
from app.investigator.tools.base import InvestigationTool
from app.investigator.tools.claim_extractor import ClaimExtractorTool
from app.investigator.tools.deepfake_tool import DeepfakeDetectionTool
from app.investigator.tools.entity_extractor import EntityExtractorTool
from app.investigator.tools.face_tool import FaceDetectionTool
from app.investigator.tools.normalizer import InputNormalizerTool
from app.investigator.tools.ocr_tool import OCRTool
from app.investigator.tools.pattern_analyzer import ScamPatternAnalyzerTool
from app.investigator.tools.url_tool import URLIntelligenceTool
from app.investigator.tools.video_tool import VideoAnalysisTool
from app.providers.deepfake import DeepfakeProvider
from app.providers.face_detector import FaceDetectorProvider
from app.providers.llm import LLMProvider
from app.providers.ocr import OCRProvider
from app.providers.stt import STTProvider
from app.providers.video_processor import VideoProcessor


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


def create_default_registry(
    llm_provider: LLMProvider,
    ocr_provider: OCRProvider | None = None,
    stt_provider: STTProvider | None = None,
    deepfake_provider: DeepfakeProvider | None = None,
    face_detector: FaceDetectorProvider | None = None,
    video_processor: VideoProcessor | None = None,
) -> ToolRegistry:
    """Create the default VERA investigative tool registry."""

    registry = ToolRegistry()

    # Phase 02 Text & Logic Tools
    registry.register(InputNormalizerTool())
    registry.register(EntityExtractorTool(llm_provider=llm_provider))
    registry.register(ClaimExtractorTool(llm_provider=llm_provider))
    registry.register(ScamPatternAnalyzerTool(llm_provider=llm_provider))

    # Phase 03 Multimodal Forensics Tools
    registry.register(OCRTool(ocr_provider=ocr_provider))
    registry.register(AudioTranscriptionTool(stt_provider=stt_provider))
    registry.register(VideoAnalysisTool(video_processor=video_processor))
    registry.register(FaceDetectionTool(face_detector=face_detector))
    registry.register(
        DeepfakeDetectionTool(
            deepfake_provider=deepfake_provider,
            face_detector=face_detector,
        )
    )

    # Phase 04 URL Intelligence
    registry.register(URLIntelligenceTool())

    return registry