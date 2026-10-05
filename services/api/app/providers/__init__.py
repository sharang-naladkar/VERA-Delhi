"""Providers package."""

from app.providers.apk_classifier import APKClassifier, UnavailableAPKClassifier
from app.providers.base import BaseProvider
from app.providers.deepfake import DeepfakeProvider, UnavailableDeepfakeProvider
from app.providers.embedding import EmbeddingProvider, UnavailableEmbeddingProvider
from app.providers.llm import LLMProvider, UnavailableLLMProvider
from app.providers.ocr import OCRProvider, UnavailableOCRProvider
from app.providers.stt import STTProvider, UnavailableSTTProvider
from app.providers.url_classifier import UnavailableURLClassifier, URLClassifier

__all__ = [
    "BaseProvider",
    "LLMProvider",
    "UnavailableLLMProvider",
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
