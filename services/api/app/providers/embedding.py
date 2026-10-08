"""Embedding providers for regulatory knowledge retrieval."""

from abc import abstractmethod
from typing import Any

from app.contracts.status import AnalysisStatus
from app.providers.base import BaseProvider


class EmbeddingProvider(BaseProvider):
    """Interface for vector embedding generation."""

    @abstractmethod
    async def embed_texts(self, texts: list[str]) -> list[list[float]]:
        """Generate vector embeddings for a list of texts."""
        pass


class UnavailableEmbeddingProvider(EmbeddingProvider):
    """Fail-safe provider used when embeddings are not configured."""

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
            "message": "Embedding model is not configured.",
        }

    async def embed_texts(self, texts: list[str]) -> list[list[float]]:
        raise NotImplementedError(
            "Embedding model is unavailable."
        )


class BGE_M3EmbeddingProvider(EmbeddingProvider):
    """BGE-M3 embedding provider backed by sentence-transformers."""

    def __init__(
        self,
        model_name: str = "BAAI/bge-m3",
    ) -> None:
        self.model_name = model_name
        self._model: Any | None = None

    @property
    def provider_name(self) -> str:
        return "bge_m3"

    @property
    def is_available(self) -> bool:
        return self._model is not None

    def _load_model(self) -> Any:
        if self._model is None:
            from sentence_transformers import SentenceTransformer

            self._model = SentenceTransformer(self.model_name)

        return self._model

    async def health_check(self) -> dict[str, Any]:
        try:
            self._load_model()
            return {
                "status": AnalysisStatus.SUCCESS.value,
                "provider": self.provider_name,
                "model": self.model_name,
            }
        except Exception as exc:
            return {
                "status": AnalysisStatus.UNAVAILABLE.value,
                "provider": self.provider_name,
                "model": self.model_name,
                "message": str(exc),
            }

    async def embed_texts(self, texts: list[str]) -> list[list[float]]:
        if not texts:
            return []

        model = self._load_model()

        embeddings = model.encode(
            texts,
            normalize_embeddings=True,
            convert_to_numpy=True,
        )

        return embeddings.tolist()