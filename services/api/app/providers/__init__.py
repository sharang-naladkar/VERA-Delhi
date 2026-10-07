"""Providers package for VERA analyzers and models."""

from app.providers.apk_classifier import APKClassifier, UnavailableAPKClassifier
from app.providers.base import BaseProvider
from app.providers.deepfake import DeepfakeProvider, UnavailableDeepfakeProvider
from app.providers.embedding import EmbeddingProvider, UnavailableEmbeddingProvider
from app.providers.factory import get_llm_provider
from app.providers.llm import LLMProvider, UnavailableLLMProvider
from app.providers.mock_llm import MockLLMProvider
from app.providers.ocr import OCRProvider, UnavailableOCRProvider
from app.providers.ollama import OllamaLLMProvider
from app.providers.stt import STTProvider, UnavailableSTTProvider
from app.providers.url_classifier import UnavailableURLClassifier, URLClassifier

__all__ = [
    "BaseProvider",
    "LLMProvider",
    "UnavailableLLMProvider",
    "OllamaLLMProvider",
    "MockLLMProvider",
    "get_llm_provider",
    "OCRProvider",
    "UnavailableOCRProvider",
    "STTProvider",
    "UnavailableSTTProvider",
    "DeepfakeProvider",
    "UnavailableDeepfakeProvider",
    "URLClassifier",
    "UnavailableURLClassifier",
    "APKClassifier",
    "UnavailableAPKClassifier",
    "EmbeddingProvider",
    "UnavailableEmbeddingProvider",
]
