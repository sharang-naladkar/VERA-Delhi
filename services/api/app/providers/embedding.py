"""Embedding Provider Interface and Unavailable Fallback."""

from abc import abstractmethod
from typing import Any

from app.contracts.status import AnalysisStatus
from app.providers.base import BaseProvider


class EmbeddingProvider(BaseProvider):
    """Interface for Vector Embedding generation for text/documents."""

    @abstractmethod
    async def embed_texts(self, texts: list[str]) -> list[list[float]]:
        """Generate high-dimensional vector embeddings for a list of texts."""
        pass


class UnavailableEmbeddingProvider(EmbeddingProvider):
    """Fail-safe placeholder for Embedding provider."""

    @property
    def provider_name(self) -> str:
        return "unavailable_embedding"

    @property
    def is_available(self) -> bool:
        return False

    async def health_check(self) -> dict[str, Any]:
        return {
            "status": AnalysisStatus.UNAVAILABLE.value,
            "provider": self.provider_name,
            "message": "Embedding model is not configured in Phase 01.",
        }

    async def embed_texts(self, texts: list[str]) -> list[list[float]]:
        raise NotImplementedError("Embedding model is unavailable in Phase 01 foundation.")
