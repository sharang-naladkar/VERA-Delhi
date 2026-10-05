"""Tests for Health and Readiness Probes."""

from unittest.mock import AsyncMock, patch

import pytest
from httpx import AsyncClient


@pytest.mark.asyncio
async def test_liveness_probe(client: AsyncClient) -> None:
    """Verify /health returns 200 and version metadata."""
    response = await client.get("/health")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "ok"
    assert "version" in data
    assert "timestamp" in data
    assert "X-Request-ID" in response.headers


@pytest.mark.asyncio
async def test_readiness_probe_all_ready(client: AsyncClient) -> None:
    """Verify /health/ready returns 200 when all backing services are healthy."""
    with (
        patch("app.services.readiness.check_database", new_callable=AsyncMock) as mock_db,
        patch("app.services.readiness.check_redis", new_callable=AsyncMock) as mock_redis,
        patch("app.services.readiness.check_minio", new_callable=AsyncMock) as mock_minio,
    ):
        mock_db.return_value = (True, {"status": "ready", "message": "DB OK", "latency_ms": 1.2})
        mock_redis.return_value = (
            True,
            {"status": "ready", "message": "Redis OK", "latency_ms": 0.8},
        )
        mock_minio.return_value = (
            True,
            {"status": "ready", "message": "MinIO OK", "latency_ms": 2.1},
        )

        response = await client.get("/health/ready")
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "ready"
        assert data["services"]["database"]["status"] == "ready"
        assert data["services"]["redis"]["status"] == "ready"
        assert data["services"]["minio"]["status"] == "ready"


@pytest.mark.asyncio
async def test_readiness_probe_dependency_failed(client: AsyncClient) -> None:
    """Verify /health/ready returns 503 when a dependency is unavailable."""
    with (
        patch("app.services.readiness.check_database", new_callable=AsyncMock) as mock_db,
        patch("app.services.readiness.check_redis", new_callable=AsyncMock) as mock_redis,
        patch("app.services.readiness.check_minio", new_callable=AsyncMock) as mock_minio,
    ):
        mock_db.return_value = (True, {"status": "ready", "message": "DB OK", "latency_ms": 1.2})
        mock_redis.return_value = (
            False,
            {"status": "unavailable", "message": "Redis down", "latency_ms": None},
        )
        mock_minio.return_value = (
            True,
            {"status": "ready", "message": "MinIO OK", "latency_ms": 2.1},
        )

        response = await client.get("/health/ready")
        assert response.status_code == 503
        data = response.json()
        assert data["status"] == "unavailable"
        assert data["services"]["redis"]["status"] == "unavailable"
