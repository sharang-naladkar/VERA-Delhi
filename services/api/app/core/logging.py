"""Structured JSON/Contextual Logging for VERA."""

import json
import logging
import sys
from contextvars import ContextVar
from typing import Any

# Context variables for request tracing
request_id_ctx: ContextVar[str | None] = ContextVar("request_id", default=None)
investigation_id_ctx: ContextVar[str | None] = ContextVar("investigation_id", default=None)

SENSITIVE_KEYS = {
    "password",
    "secret",
    "token",
    "access_key",
    "secret_key",
    "authorization",
    "api_key",
}


def sanitize_data(data: Any) -> Any:
    """Recursively scrub sensitive keys from log payloads."""
    if isinstance(data, dict):
        sanitized = {}
        for k, v in data.items():
            if any(sensitive in k.lower() for sensitive in SENSITIVE_KEYS):
                sanitized[k] = "[REDACTED]"
            else:
                sanitized[k] = sanitize_data(v)
        return sanitized
    elif isinstance(data, list):
        return [sanitize_data(item) for item in data]
    return data


class StructuredFormatter(logging.Formatter):
    """JSON Structured log formatter."""

    def format(self, record: logging.LogRecord) -> str:
        log_entry: dict[str, Any] = {
            "timestamp": self.formatTime(record, self.datefmt),
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
            "request_id": request_id_ctx.get(),
            "investigation_id": investigation_id_ctx.get(),
        }

        # Include custom extra fields attached to record
        if hasattr(record, "extra_fields") and isinstance(record.extra_fields, dict):
            log_entry.update(sanitize_data(record.extra_fields))

        if record.exc_info:
            log_entry["exception"] = self.formatException(record.exc_info)

        return json.dumps(log_entry, default=str)


def setup_logging(debug: bool = False) -> None:
    """Initialize structured application logging."""
    root_logger = logging.getLogger()
    root_logger.setLevel(logging.DEBUG if debug else logging.INFO)

    # Remove existing handlers to avoid duplicates
    for handler in list(root_logger.handlers):
        root_logger.removeHandler(handler)

    handler = logging.StreamHandler(sys.stdout)
    formatter = StructuredFormatter()
    handler.setFormatter(formatter)
    root_logger.addHandler(handler)

    # Silence overly verbose external loggers
    logging.getLogger("uvicorn.access").setLevel(logging.WARNING)


def get_logger(name: str) -> logging.Logger:
    """Return a logger instance with helper methods."""
    return logging.getLogger(name)


class StructuredLoggerAdapter(logging.LoggerAdapter):
    """Adapter to easily pass structured context dictionary."""

    def process(self, msg: Any, kwargs: dict[str, Any]) -> tuple[Any, dict[str, Any]]:
        extra = kwargs.get("extra", {})
        if "extra_fields" not in extra:
            extra["extra_fields"] = self.extra
        kwargs["extra"] = extra
        return msg, kwargs
