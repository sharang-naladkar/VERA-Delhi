"""Tests for Investigation Endpoints and Error Handling."""

import uuid

import pytest
from httpx import AsyncClient


@pytest.mark.asyncio
async def test_create_investigation_success(client: AsyncClient) -> None:
    """Verify POST /v1/investigations creates a new investigation record."""
    payload = {
        "title": "Telegram VIP Trading Scam",
        "description": "User reported promise of 500% guaranteed monthly returns.",
        "metadata": {"source_platform": "telegram", "channel_id": "@guaranteed_profits_india"},
    }

    response = await client.post("/v1/investigations", json=payload)
    assert response.status_code == 201
    data = response.json()

    assert "id" in data
    assert uuid.UUID(data["id"])  # Valid UUID
    assert data["title"] == "Telegram VIP Trading Scam"
    assert data["status"] == "created"
    assert "vera_version" in data
    assert "created_at" in data
    assert "updated_at" in data
    assert "X-Request-ID" in response.headers


@pytest.mark.asyncio
async def test_create_investigation_empty_payload(client: AsyncClient) -> None:
    """Verify POST /v1/investigations works without body."""
    response = await client.post("/v1/investigations", json={})
    assert response.status_code == 201
    data = response.json()
    assert "id" in data
    assert data["status"] == "created"


@pytest.mark.asyncio
async def test_get_investigation_by_id_success(client: AsyncClient) -> None:
    """Verify GET /v1/investigations/{id} returns created record."""
    create_resp = await client.post(
        "/v1/investigations",
        json={"title": "Test Scheme", "description": "Fake SEBI certificate"},
    )
    inv_id = create_resp.json()["id"]

    get_resp = await client.get(f"/v1/investigations/{inv_id}")
    assert get_resp.status_code == 200
    data = get_resp.json()
    assert data["id"] == inv_id
    assert data["title"] == "Test Scheme"
    assert data["status"] == "created"


@pytest.mark.asyncio
async def test_get_investigation_not_found(client: AsyncClient) -> None:
    """Verify GET /v1/investigations/{id} returns structured 404 for missing ID."""
    random_id = str(uuid.uuid4())
    response = await client.get(f"/v1/investigations/{random_id}")
    assert response.status_code == 404
    data = response.json()
    assert "error" in data
    assert data["error"]["code"] == "NOT_FOUND"
    assert "not found" in data["error"]["message"].lower()
    assert data["error"]["request_id"] is not None


@pytest.mark.asyncio
async def test_get_investigation_invalid_uuid(client: AsyncClient) -> None:
    """Verify GET /v1/investigations/{id} returns structured 422 for malformed UUID."""
    response = await client.get("/v1/investigations/not-a-valid-uuid")
    assert response.status_code == 422
    data = response.json()
    assert "error" in data
    assert data["error"]["code"] == "VALIDATION_ERROR"
    assert data["error"]["request_id"] is not None
