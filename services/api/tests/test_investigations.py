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

@pytest.mark.asyncio
async def test_regulatory_only_investigation_preserves_unavailable_result(
    client: AsyncClient,
) -> None:
    """A structured request runs without text and never invents a match."""
    response = await client.post(
        "/v1/investigations",
        json={
            "title": "Regulatory verification test",
            "regulatory_verification_request": {
                "participant_type": "investment_adviser",
                "subject_name": "Example Adviser",
            },
        },
    )

    assert response.status_code == 201
    data = response.json()
    state = data["state"]
    assert state is not None

    results = [
        item
        for item in state["tool_results"]
        if item.get("tool_name") == "regulatory_verification"
    ]

    assert len(results) == 1
    assert results[0]["status"] == "UNAVAILABLE"
    assert results[0]["output_data"]["matched"] is None
    assert (
        results[0]["output_data"]["verification_status"]
        == "UNAVAILABLE"
    )


@pytest.mark.asyncio
async def test_regulatory_request_without_identifier_is_rejected(
    client: AsyncClient,
) -> None:
    """Invalid regulatory requests fail API validation before investigation."""
    response = await client.post(
        "/v1/investigations",
        json={
            "regulatory_verification_request": {
                "participant_type": "investment_adviser",
            },
        },
    )

    assert response.status_code == 422


@pytest.mark.asyncio
async def test_regulatory_request_with_unknown_participant_type_is_rejected(
    client: AsyncClient,
) -> None:
    """Unknown participant types are rejected by the typed API contract."""
    response = await client.post(
        "/v1/investigations",
        json={
            "regulatory_verification_request": {
                "participant_type": "unknown_participant",
                "subject_name": "Example Adviser",
            },
        },
    )

    assert response.status_code == 422
