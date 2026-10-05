"""Health and Readiness Probes."""

from datetime import UTC, datetime
from typing import Any

from fastapi import APIRouter, Response, status

from app.core.config import settings
from app.services.readiness import evaluate_system_readiness

router = APIRouter(tags=["System"])


@router.get("/health", status_code=status.HTTP_200_OK)
async def get_health() -> dict[str, Any]:
    """Liveness probe: verifies the API worker is running."""
    return {
        "status": "ok",
        "version": settings.APP_VERSION,
        "timestamp": datetime.now(UTC).isoformat(),
    }


@router.get("/health/ready")
async def get_readiness(response: Response) -> dict[str, Any]:
    """Readiness probe: validates all backing services (DB, Redis, MinIO)."""
    is_ready, readiness_data = await evaluate_system_readiness()

    readiness_payload = {
        "status": readiness_data["status"],
        "timestamp": datetime.now(UTC).isoformat(),
        "services": readiness_data["services"],
    }

    if not is_ready:
        response.status_code = status.HTTP_503_SERVICE_UNAVAILABLE
    else:
        response.status_code = status.HTTP_200_OK

    return readiness_payload
