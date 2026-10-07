"""Providers package for VERA analyzers and models."""

from app.providers.apk_classifier import APKClassifier, UnavailableAPKClassifier
from app.providers.base import BaseProvider
from app.providers.deepfake import (
    DeepfakeProvider,
    MesoNetDeepfakeProvider,
    MockDeepfakeProvider,
    UnavailableDeepfakeProvider,
)
from app.providers.embedding import EmbeddingProvider, UnavailableEmbeddingProvider
from app.providers.face_detector import (
    FaceDetectorProvider,
    MockFaceDetectorProvider,
    OpenCVFaceDetectorProvider,
    UnavailableFaceDetectorProvider,
)
from app.providers.factory import (
    get_deepfake_provider,
    get_face_detector_provider,
    get_llm_provider,
    get_ocr_provider,
    get_stt_provider,
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
from app.providers.url_classifier import UnavailableURLClassifier, URLClassifier
from app.providers.video_processor import VideoProcessor

__all__ = [
    "BaseProvider",
    "LLMProvider",
    "UnavailableLLMProvider",
    "OllamaLLMProvider",
    "MockLLMProvider",
    "get_llm_provider",
    "OCRProvider",
    "PaddleOCRProvider",
    "MockOCRProvider",
    "UnavailableOCRProvider",
    "get_ocr_provider",
    "STTProvider",
    "FasterWhisperSTTProvider",
    "MockSTTProvider",
    "UnavailableSTTProvider",
    "get_stt_provider",
    "DeepfakeProvider",
    "MesoNetDeepfakeProvider",
    "MockDeepfakeProvider",
    "UnavailableDeepfakeProvider",
    "get_deepfake_provider",
    "FaceDetectorProvider",
    "OpenCVFaceDetectorProvider",
    "MockFaceDetectorProvider",
    "UnavailableFaceDetectorProvider",
    "get_face_detector_provider",
    "VideoProcessor",
    "URLClassifier",
    "UnavailableURLClassifier",
    "APKClassifier",
    "UnavailableAPKClassifier",
    "EmbeddingProvider",
    "UnavailableEmbeddingProvider",
]
