"""VERA FastAPI Application Entrypoint."""

import time
import uuid
from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request, Response
from fastapi.middleware.cors import CORSMiddleware
from starlette.middleware.base import BaseHTTPMiddleware

from app.api.routes import health_router, investigations_router
from app.core.config import settings
from app.core.errors import register_error_handlers
from app.core.logging import get_logger, request_id_ctx, setup_logging
from app.db.database import Base, engine

logger = get_logger("app.main")


class RequestContextMiddleware(BaseHTTPMiddleware):
    """Middleware for assigning Request IDs and tracking request duration."""

    async def dispatch(self, request: Request, call_next) -> Response:
        req_id = request.headers.get("X-Request-ID") or f"req-{uuid.uuid4()}"
        token = request_id_ctx.set(req_id)
        start_time = time.perf_counter()

        try:
            response = await call_next(request)
            duration_ms = round((time.perf_counter() - start_time) * 1000, 2)
            response.headers["X-Request-ID"] = req_id
            response.headers["X-Response-Time-Ms"] = str(duration_ms)

            # Do not spam logs for liveness checks unless debugging
            if request.url.path not in ("/health",):
                logger.info(
                    f"{request.method} {request.url.path} -> {response.status_code} ({duration_ms}ms)",
                    extra={
                        "extra_fields": {
                            "method": request.method,
                            "path": request.url.path,
                            "status_code": response.status_code,
                            "duration_ms": duration_ms,
                        }
                    },
                )
            return response
        except Exception:
            duration_ms = round((time.perf_counter() - start_time) * 1000, 2)
            logger.error(
                f"{request.method} {request.url.path} failed after {duration_ms}ms",
                exc_info=True,
                extra={
                    "extra_fields": {
                        "method": request.method,
                        "path": request.url.path,
                        "duration_ms": duration_ms,
                    }
                },
            )
            raise
        finally:
            request_id_ctx.reset(token)


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
    """Lifecycle events for FastAPI application."""
    setup_logging(debug=settings.DEBUG)
    logger.info(
        f"Starting {settings.APP_NAME} API v{settings.APP_VERSION} ({settings.APP_ENV})",
        extra={"extra_fields": {"version": settings.APP_VERSION, "env": settings.APP_ENV}},
    )

    # Initialize tables if needed (e.g. SQLite / dev fallback)
    try:
        async with engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)
        logger.info("Database schema initialized successfully.")
    except Exception as exc:
        logger.warning(f"Could not automatically sync database metadata on startup: {exc}")

    yield

    logger.info(f"Shutting down {settings.APP_NAME} API.")
    await engine.dispose()


def create_app() -> FastAPI:
    """Application factory for VERA backend."""
    app = FastAPI(
        title=f"{settings.APP_NAME} - Agentic AI Investment Fraud Investigation API",
        version=settings.APP_VERSION,
        description="Foundation API for the VERA autonomous investment fraud detection platform.",
        lifespan=lifespan,
        docs_url="/docs",
        redoc_url="/redoc",
        openapi_url="/openapi.json",
    )

    # Middleware
    app.add_middleware(RequestContextMiddleware)
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origins_list,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    # Centralized Exception Handlers
    register_error_handlers(app)

    # Routers
    app.include_router(health_router)
    app.include_router(investigations_router)

    return app


app = create_app()
