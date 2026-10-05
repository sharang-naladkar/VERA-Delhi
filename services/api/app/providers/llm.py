"""LLM Provider Interface and Unavailable Fallback."""

from abc import abstractmethod
from typing import Any
from uuid import UUID

from app.contracts.status import AnalysisStatus
from app.providers.base import BaseProvider


class LLMProvider(BaseProvider):
    """Interface for LLM reasoning and investigation providers."""

    @abstractmethod
    async def chat(
        self,
        messages: list[dict[str, str]],
        temperature: float = 0.1,
        max_tokens: int | None = None,
        **kwargs: Any,
    ) -> dict[str, Any]:
        """Send a chat completion request to the LLM backend."""
        pass

    @abstractmethod
    async def analyze_fraud_claim(
        self,
        investigation_id: UUID,
        claim_text: str,
        context: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        """Analyze a specific claim for fraud indicators."""
        pass


class UnavailableLLMProvider(LLMProvider):
    """Fail-safe placeholder provider indicating LLM backend is not configured/available."""

    def __init__(self, model_name: str = "unconfigured") -> None:
        self.model_name = model_name

    @property
    def provider_name(self) -> str:
        return f"unavailable_llm:{self.model_name}"

    @property
    def is_available(self) -> bool:
        return False

    async def health_check(self) -> dict[str, Any]:
        return {
            "status": AnalysisStatus.UNAVAILABLE.value,
            "provider": self.provider_name,
            "message": "LLM provider is not configured in Phase 01 foundation.",
        }

    async def chat(
        self,
        messages: list[dict[str, str]],
        temperature: float = 0.1,
        max_tokens: int | None = None,
        **kwargs: Any,
    ) -> dict[str, Any]:
        return {
            "status": AnalysisStatus.UNAVAILABLE.value,
            "provider": self.provider_name,
            "error": "LLM provider is unavailable.",
            "response": None,
        }

    async def analyze_fraud_claim(
        self,
        investigation_id: UUID,
        claim_text: str,
        context: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        return {
            "status": AnalysisStatus.UNAVAILABLE.value,
            "provider": self.provider_name,
            "investigation_id": str(investigation_id),
            "error": "LLM analysis is not available in Phase 01.",
            "evidence": None,
        }
