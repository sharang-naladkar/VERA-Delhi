"""Provider factory functions."""

from typing import Any

from app.core.config import settings
from app.providers.llm import LLMProvider, UnavailableLLMProvider
from app.providers.mock_llm import MockLLMProvider
from app.providers.ollama import OllamaLLMProvider


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
