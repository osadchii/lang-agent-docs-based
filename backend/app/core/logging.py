"""Structured logging helpers and request context utilities."""

from __future__ import annotations

import json
import logging
import sys
from contextvars import ContextVar, Token
from datetime import datetime, timezone
from typing import Any, Final

REQUEST_ID_CTX: Final[ContextVar[str | None]] = ContextVar("request_id", default=None)

_LOGGING_CONFIGURED: bool = False


class JsonLogFormatter(logging.Formatter):
    """Serialize log records into a JSON structure suitable for log aggregation."""

    EXTRA_FIELDS: Final[tuple[str, ...]] = (
        "event",
        "http_method",
        "http_path",
        "status_code",
        "duration_ms",
        "client_ip",
        "user_agent",
    )

    def format(self, record: logging.LogRecord) -> str:
        log_entry: dict[str, Any] = {
            "ts": datetime.fromtimestamp(record.created, tz=timezone.utc).isoformat(),
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
        }

        request_id = get_request_id()
        if request_id:
            log_entry["request_id"] = request_id

        for field in self.EXTRA_FIELDS:
            value = getattr(record, field, None)
            if value is not None:
                log_entry[field] = value

        if record.exc_info:
            log_entry["exc_info"] = self.formatException(record.exc_info)

        if record.stack_info:
            log_entry["stack"] = self.formatStack(record.stack_info)

        return json.dumps(log_entry, ensure_ascii=True)


def configure_logging(level_name: str) -> None:
    """Configure root logging once with the JSON formatter."""

    global _LOGGING_CONFIGURED
    if _LOGGING_CONFIGURED:
        return

    resolved_level = _resolve_level(level_name)

    handler = logging.StreamHandler(stream=sys.stdout)
    handler.setFormatter(JsonLogFormatter())

    root_logger = logging.getLogger()
    root_logger.handlers.clear()
    root_logger.addHandler(handler)
    root_logger.setLevel(resolved_level)

    logging.captureWarnings(True)
    _LOGGING_CONFIGURED = True


def _resolve_level(level_name: str) -> int:
    try:
        level_value: int | str = logging.getLevelName(level_name.upper())
    except AttributeError:
        return logging.INFO

    if isinstance(level_value, str):
        return logging.INFO
    return int(level_value)


def bind_request_id(request_id: str) -> Token[str | None]:
    """Bind a request_id to the current context."""
    return REQUEST_ID_CTX.set(request_id)


def get_request_id() -> str | None:
    """Return the request_id bound to the current context, if any."""
    return REQUEST_ID_CTX.get()


def reset_request_id(token: Token[str | None]) -> None:
    """Reset the request_id context using the provided token."""
    REQUEST_ID_CTX.reset(token)


__all__ = [
    "JsonLogFormatter",
    "bind_request_id",
    "configure_logging",
    "get_request_id",
    "reset_request_id",
]
