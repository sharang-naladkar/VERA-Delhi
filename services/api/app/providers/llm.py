"""LLM Provider Interface and Unavailable Fallback."""

from abc import abstractmethod
from typing import Any, TypeVar
from uuid import UUID

from pydantic import BaseModel

from app.contracts.status import AnalysisStatus
from app.core.errors import ProviderUnavailableError
from app.providers.base import BaseProvider

T = TypeVar("T", bound=BaseModel)


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
    async def generate_structured(
        self,
        schema: type[T],
        prompt: str,
        system_prompt: str | None = None,
        temperature: float = 0.1,
        **kwargs: Any,
    ) -> T:
        """Generate structured Pydantic output using the LLM."""
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
            "message": "LLM provider is not configured or currently unavailable.",
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

    async def generate_structured(
        self,
        schema: type[T],
        prompt: str,
        system_prompt: str | None = None,
        temperature: float = 0.1,
        **kwargs: Any,
    ) -> T:
        raise ProviderUnavailableError(self.provider_name, details={"reason": "LLM provider is not configured or unavailable."})

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
            "error": "LLM analysis is not available.",
            "evidence": None,
        }
