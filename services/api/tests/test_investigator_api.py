"""Tests for Phase 02 Investigation API endpoints with LangGraph execution."""

import uuid

import pytest
from httpx import AsyncClient

from app.api.deps import get_llm_provider_dep
from app.contracts.status import AnalysisStatus
from app.main import app
from app.providers.mock_llm import MockLLMProvider


@pytest.mark.asyncio
async def test_api_investigation_with_text_executes_graph(client: AsyncClient) -> None:
    """Verifies POST /v1/investigations with 'text' executes LangGraph and persists results."""
    payload = {
        "title": "VIP Telegram Guaranteed Profits",
        "text": "Join VIP Trading Telegram group! Guaranteed 200% return in 30 days! Contact @vip_profits",
        "input_type": "message",
        "metadata": {"source": "telegram"},
    }

    response = await client.post("/v1/investigations", json=payload)
    assert response.status_code == 201
    data = response.json()

    assert "id" in data
    assert uuid.UUID(data["id"])
    assert data["title"] == "VIP Telegram Guaranteed Profits"
    assert data["status"] in (AnalysisStatus.SUCCESS.value, AnalysisStatus.PARTIAL.value)
    assert data["evidence_count"] >= 3
    assert len(data["evidence"]) >= 3
    assert data["result_summary"] is not None
    assert "state" in data
    assert data["state"]["normalized_input"] != ""

    # Verify GET /v1/investigations/{id} retrieves the persisted state and evidence
    get_resp = await client.get(f"/v1/investigations/{data['id']}")
    assert get_resp.status_code == 200
    get_data = get_resp.json()
    assert get_data["id"] == data["id"]
    assert get_data["status"] == data["status"]
    assert get_data["evidence_count"] == data["evidence_count"]
    assert len(get_data["evidence"]) == len(data["evidence"])


@pytest.mark.asyncio
async def test_api_investigation_empty_text_insufficient_evidence(client: AsyncClient) -> None:
    """Verifies POST /v1/investigations with empty text results in INSUFFICIENT_EVIDENCE."""
    payload = {
        "title": "Blank inquiry",
        "text": "   ",
        "input_type": "text",
    }

    response = await client.post("/v1/investigations", json=payload)
    assert response.status_code == 201
    data = response.json()
    assert data["status"] == AnalysisStatus.INSUFFICIENT_EVIDENCE.value


@pytest.mark.asyncio
async def test_api_investigation_offline_llm_controlled_failure(client: AsyncClient) -> None:
    """Verifies API returns controlled PARTIAL/FAILED status without throwing 500 when LLM is unavailable."""
    app.dependency_overrides[get_llm_provider_dep] = lambda: MockLLMProvider(mode="unavailable")

    payload = {
        "title": "Crypto Returns",
        "text": "Send crypto to get 500% profit guaranteed in 24 hours",
    }

    response = await client.post("/v1/investigations", json=payload)
    assert response.status_code == 201
    data = response.json()

    # Controlled fail-safe status
    assert data["status"] in (AnalysisStatus.PARTIAL.value, AnalysisStatus.FAILED.value)
    assert data["evidence_count"] >= 1  # Normalizer succeeded
    # Verifies internal stack trace is not exposed
    assert "traceback" not in str(data).lower()
