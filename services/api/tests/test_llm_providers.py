"""Tests for LLM Providers (MockLLMProvider and OllamaLLMProvider)."""

from uuid import uuid4

import pytest

from app.contracts.status import AnalysisStatus
from app.core.errors import LLMGenerationError, ProviderUnavailableError
from app.investigator.schemas import (
    ClaimExtraction,
    ClaimType,
    EntityExtraction,
    EntityType,
    InvestigationPlan,
    ScamPatternAnalysis,
)
from app.providers.mock_llm import MockLLMProvider
from app.providers.ollama import OllamaLLMProvider


@pytest.mark.asyncio
async def test_mock_llm_clean_text() -> None:
    """Verifies MockLLMProvider produces benign observations for clean text."""
    provider = MockLLMProvider(mode="clean")
    assert provider.is_available is True

    entities: EntityExtraction = await provider.generate_structured(
        EntityExtraction, prompt="Tata Consultancy Services announced Q3 results."
    )
    assert len(entities.entities) > 0
    assert entities.entities[0].entity_type == EntityType.ORGANIZATION

    claims: ClaimExtraction = await provider.generate_structured(
        ClaimExtraction, prompt="Company reported 5% profit growth."
    )
    assert len(claims.claims) == 0

    patterns: ScamPatternAnalysis = await provider.generate_structured(
        ScamPatternAnalysis, prompt="Clean market announcement."
    )
    assert len(patterns.patterns) == 0
    assert len(patterns.indicators) == 0


@pytest.mark.asyncio
async def test_mock_llm_guaranteed_return_message() -> None:
    """Verifies MockLLMProvider detects guaranteed return signals."""
    provider = MockLLMProvider(mode="guaranteed_return")

    claims: ClaimExtraction = await provider.generate_structured(
        ClaimExtraction, prompt="Join now for guaranteed 200% monthly returns!"
    )
    assert len(claims.claims) >= 1
    guaranteed = any(c.claim_type == ClaimType.GUARANTEED_RETURNS for c in claims.claims)
    assert guaranteed is True

    patterns: ScamPatternAnalysis = await provider.generate_structured(
        ScamPatternAnalysis, prompt="Join now for guaranteed 200% monthly returns!"
    )
    assert len(patterns.patterns) >= 1
    assert any("guaranteed" in p.lower() for p in patterns.patterns)


@pytest.mark.asyncio
async def test_mock_llm_impersonation_message() -> None:
    """Verifies MockLLMProvider detects advisor and regulatory registration assertions."""
    provider = MockLLMProvider(mode="impersonation")

    entities: EntityExtraction = await provider.generate_structured(
        EntityExtraction, prompt="Contact Rajesh Sharma, SEBI Reg No INA000099999"
    )
    assert len(entities.entities) >= 1
    types = [e.entity_type for e in entities.entities]
    assert EntityType.ADVISOR in types or EntityType.REGISTRATION_NUMBER in types

    claims: ClaimExtraction = await provider.generate_structured(
        ClaimExtraction, prompt="SEBI registered advisor insider tips"
    )
    assert any(c.claim_type == ClaimType.SEBI_REGISTRATION for c in claims.claims)


@pytest.mark.asyncio
async def test_mock_llm_insufficient_evidence() -> None:
    """Verifies MockLLMProvider handles sparse/insufficient text appropriately."""
    provider = MockLLMProvider(mode="insufficient_evidence")

    entities: EntityExtraction = await provider.generate_structured(
        EntityExtraction, prompt="Hi"
    )
    assert len(entities.entities) == 0

    claims: ClaimExtraction = await provider.generate_structured(
        ClaimExtraction, prompt="Hi"
    )
    assert len(claims.claims) == 0

    patterns: ScamPatternAnalysis = await provider.generate_structured(
        ScamPatternAnalysis, prompt="Hi"
    )
    assert "insufficient" in patterns.explanation.lower()


@pytest.mark.asyncio
async def test_mock_llm_malformed_output() -> None:
    """Verifies MockLLMProvider raises LLMGenerationError in malformed mode."""
    provider = MockLLMProvider(mode="malformed")
    with pytest.raises(LLMGenerationError) as exc_info:
        await provider.generate_structured(
            EntityExtraction, prompt="test prompt"
        )
    assert "malformed" in str(exc_info.value).lower()


@pytest.mark.asyncio
async def test_mock_llm_unavailable_mode() -> None:
    """Verifies MockLLMProvider raises ProviderUnavailableError in unavailable mode."""
    provider = MockLLMProvider(mode="unavailable")
    assert provider.is_available is False

    health = await provider.health_check()
    assert health["status"] == AnalysisStatus.UNAVAILABLE.value

    with pytest.raises(ProviderUnavailableError):
        await provider.generate_structured(
            EntityExtraction, prompt="test prompt"
        )


@pytest.mark.asyncio
async def test_ollama_provider_configuration_and_offline_handling() -> None:
    """Verifies OllamaLLMProvider configurations and controlled fail-safe error handling when unreachable."""
    provider = OllamaLLMProvider(
        base_url="http://127.0.0.1:99999",  # Non-existent port
        model="qwen3:8b",
        timeout_seconds=2.0,
        temperature=0.2,
    )
    assert provider.provider_name == "ollama:qwen3:8b"
    assert provider.base_url == "http://127.0.0.1:99999"

    # Health check must return controlled UNAVAILABLE status, not crash
    health = await provider.health_check()
    assert health["status"] == AnalysisStatus.UNAVAILABLE.value

    # Chat must return controlled UNAVAILABLE status, not crash
    chat_resp = await provider.chat([{"role": "user", "content": "hello"}])
    assert chat_resp["status"] == AnalysisStatus.UNAVAILABLE.value
    assert chat_resp["response"] is None

    # generate_structured must raise controlled ProviderUnavailableError
    with pytest.raises(ProviderUnavailableError) as exc:
        await provider.generate_structured(
            EntityExtraction, prompt="hello"
        )
    assert "ollama:qwen3:8b" in str(exc.value)


def test_ollama_json_substring_cleaning() -> None:
    """Verifies Ollama JSON cleaner strips markdown wrappers and extraneous text."""
    raw = "```json\n{\"entities\": [], \"summary\": \"none\"}\n```"
    cleaned = OllamaLLMProvider._clean_json_substring(raw)
    assert cleaned == "{\"entities\": [], \"summary\": \"none\"}"

    wrapped = "Here is the result: {\"name\": \"test\"} Hope this helps!"
    cleaned2 = OllamaLLMProvider._clean_json_substring(wrapped)
    assert cleaned2 == "{\"name\": \"test\"}"
