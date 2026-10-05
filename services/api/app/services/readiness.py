"""Readiness and Health Probe Service."""

import time
from typing import Any

import httpx
import redis.asyncio as aioredis
from sqlalchemy import text

from app.core.config import settings
from app.core.logging import get_logger
from app.db.database import engine

logger = get_logger("app.readiness")


async def check_database() -> tuple[bool, dict[str, Any]]:
    """Probe PostgreSQL database connectivity."""
    start_time = time.perf_counter()
    try:
        async with engine.connect() as conn:
            await conn.execute(text("SELECT 1"))
        latency = round((time.perf_counter() - start_time) * 1000, 2)
        return True, {
            "status": "ready",
            "message": "Database connection verified",
            "latency_ms": latency,
        }
    except Exception as exc:
        logger.warning(f"Database readiness check failed: {exc}")
        return False, {
            "status": "unavailable",
            "message": f"Database unreachable: {str(exc)}",
            "latency_ms": None,
        }


async def check_redis() -> tuple[bool, dict[str, Any]]:
    """Probe Redis cache connectivity."""
    start_time = time.perf_counter()
    try:
        r = aioredis.from_url(settings.REDIS_URL, socket_connect_timeout=2.0, socket_timeout=2.0)
        await r.ping()
        await r.aclose()
        latency = round((time.perf_counter() - start_time) * 1000, 2)
        return True, {
            "status": "ready",
            "message": "Redis connection verified",
            "latency_ms": latency,
        }
    except Exception as exc:
        logger.warning(f"Redis readiness check failed: {exc}")
        return False, {
            "status": "unavailable",
            "message": f"Redis unreachable: {str(exc)}",
            "latency_ms": None,
        }


async def check_minio() -> tuple[bool, dict[str, Any]]:
    """Probe MinIO / S3 object storage connectivity."""
    start_time = time.perf_counter()
    endpoint = settings.MINIO_ENDPOINT.rstrip("/")
    probe_url = f"{endpoint}/minio/health/live"
    try:
        async with httpx.AsyncClient(timeout=2.0) as client:
            resp = await client.get(probe_url)
            # MinIO returns 200 on /minio/health/live; or 403 on root if auth required
            if resp.status_code in (200, 403, 400):
                latency = round((time.perf_counter() - start_time) * 1000, 2)
                return True, {
                    "status": "ready",
                    "message": "MinIO storage endpoint reachable",
                    "latency_ms": latency,
                }
            else:
                return False, {
                    "status": "degraded",
                    "message": f"MinIO returned status code {resp.status_code}",
                    "latency_ms": None,
                }
    except Exception as exc:
        logger.warning(f"MinIO readiness check failed: {exc}")
        return False, {
            "status": "unavailable",
            "message": f"MinIO unreachable: {str(exc)}",
            "latency_ms": None,
        }


async def evaluate_system_readiness() -> tuple[bool, dict[str, Any]]:
    """Evaluate full system readiness across all backing services."""
    db_ok, db_info = await check_database()
    redis_ok, redis_info = await check_redis()
    minio_ok, minio_info = await check_minio()

    all_ready = db_ok and redis_ok and minio_ok
    overall_status = "ready" if all_ready else "unavailable"

    services = {
        "database": db_info,
        "redis": redis_info,
        "minio": minio_info,
    }

    return all_ready, {
        "status": overall_status,
        "services": services,
    }
