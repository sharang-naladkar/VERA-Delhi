"""Provider factory functions."""

from typing import Any

from app.core.config import settings
from app.core.logging import get_logger
from app.providers.deepfake import (
    DeepfakeProvider,
    MesoNetDeepfakeProvider,
    MockDeepfakeProvider,
    UnavailableDeepfakeProvider,
)
from app.providers.face_detector import (
    FaceDetectorProvider,
    MockFaceDetectorProvider,
    OpenCVFaceDetectorProvider,
    UnavailableFaceDetectorProvider,
)
from app.providers.llm import LLMProvider, UnavailableLLMProvider
from app.providers.mock_llm import MockLLMProvider
from app.providers.ocr import (
    MockOCRProvider,
    OCRProvider,
    PaddleOCRProvider,
    UnavailableOCRProvider,
)
from app.providers.ollama import OllamaLLMProvider
from app.providers.stt import (
    FasterWhisperSTTProvider,
    MockSTTProvider,
    STTProvider,
    UnavailableSTTProvider,
)

logger = get_logger("app.providers.factory")


def get_llm_provider(settings_override: Any | None = None) -> LLMProvider:
    """Factory to retrieve configured LLM provider based on application settings."""
    cfg = settings_override or settings
    provider_name = (getattr(cfg, "LLM_PROVIDER", None) or "unavailable").lower().strip()

    if provider_name in ("ollama", "qwen3"):
        return OllamaLLMProvider(
            base_url=getattr(cfg, "OLLAMA_BASE_URL", "http://localhost:11434"),
            model=getattr(cfg, "LLM_MODEL", "qwen3:8b"),
            timeout_seconds=getattr(cfg, "LLM_TIMEOUT_SECONDS", 60.0),
            temperature=getattr(cfg, "LLM_TEMPERATURE", 0.1),
        )
    if provider_name == "mock":
        return MockLLMProvider(model_name=getattr(cfg, "LLM_MODEL", "mock-qwen3"))
    return UnavailableLLMProvider(model_name=getattr(cfg, "LLM_MODEL", "unconfigured"))


def get_ocr_provider(settings_override: Any | None = None) -> OCRProvider:
    """Factory to retrieve configured OCR provider based on application settings."""
    cfg = settings_override or settings
    provider_name = (getattr(cfg, "OCR_PROVIDER", None) or "unavailable").lower().strip()

    if provider_name == "paddleocr":
        try:
            return PaddleOCRProvider()
        except Exception as exc:
            logger.warning(f"Failed to instantiate PaddleOCR provider: {exc}. Falling back to unavailable.")
            return UnavailableOCRProvider()
    if provider_name == "mock":
        return MockOCRProvider()
    return UnavailableOCRProvider()


def get_stt_provider(settings_override: Any | None = None) -> STTProvider:
    """Factory to retrieve configured Speech-to-Text provider based on application settings."""
    cfg = settings_override or settings
    provider_name = (getattr(cfg, "STT_PROVIDER", None) or "unavailable").lower().strip()

    if provider_name in ("faster_whisper", "whisper"):
        try:
            return FasterWhisperSTTProvider()
        except Exception as exc:
            logger.warning(f"Failed to instantiate faster-whisper provider: {exc}. Falling back to unavailable.")
            return UnavailableSTTProvider()
    if provider_name == "mock":
        return MockSTTProvider()
    return UnavailableSTTProvider()


def get_face_detector_provider(settings_override: Any | None = None) -> FaceDetectorProvider:
    """Factory to retrieve configured Face Detection provider based on application settings."""
    cfg = settings_override or settings
    provider_name = (getattr(cfg, "FACE_DETECTOR_PROVIDER", None) or "opencv").lower().strip()

    if provider_name in ("opencv", "haar"):
        try:
            return OpenCVFaceDetectorProvider()
        except Exception as exc:
            logger.warning(f"Failed to instantiate OpenCV face detector: {exc}. Falling back to unavailable.")
            return UnavailableFaceDetectorProvider()
    if provider_name == "mock":
        return MockFaceDetectorProvider()
    return UnavailableFaceDetectorProvider()


def get_deepfake_provider(settings_override: Any | None = None) -> DeepfakeProvider:
    """Factory to retrieve configured Deepfake Detection provider based on application settings."""
    cfg = settings_override or settings
    provider_name = (getattr(cfg, "DEEPFAKE_PROVIDER", None) or "unavailable").lower().strip()

    if provider_name in ("mesonet", "meso4"):
        weights_path = getattr(cfg, "MESONET_WEIGHTS_PATH", None)
        try:
            return MesoNetDeepfakeProvider(weights_path=weights_path)
        except Exception as exc:
            logger.warning(f"Failed to instantiate MesoNet provider: {exc}. Falling back to unavailable.")
            return UnavailableDeepfakeProvider()
    if provider_name == "mock":
        return MockDeepfakeProvider()
    return UnavailableDeepfakeProvider()
