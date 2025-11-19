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

    RESERVED_ATTRS: Final[frozenset[str]] = frozenset(
        {
            "args",
            "asctime",
            "created",
            "exc_info",
            "exc_text",
            "filename",
            "funcName",
            "levelname",
            "levelno",
            "lineno",
            "module",
            "msecs",
            "message",
            "msg",
            "name",
            "pathname",
            "process",
            "processName",
            "relativeCreated",
            "stack_info",
            "thread",
            "threadName",
            "request_id",
        }
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

        extra_fields = self._extract_extra_fields(record)
        if extra_fields:
            log_entry.update(extra_fields)

        if record.exc_info:
            # Replace newlines with space to keep single-line JSON
            exc_text = self.formatException(record.exc_info)
            log_entry["exc_info"] = exc_text.replace("\n", " | ")

        if record.stack_info:
            # Replace newlines with space to keep single-line JSON
            stack_text = self.formatStack(record.stack_info)
            log_entry["stack"] = stack_text.replace("\n", " | ")

        # Ensure single-line JSON output (no indentation)
        return json.dumps(log_entry, ensure_ascii=True, separators=(",", ":"))

    def _extract_extra_fields(self, record: logging.LogRecord) -> dict[str, Any]:
        extras: dict[str, Any] = {}
        for key, value in record.__dict__.items():
            if key in self.RESERVED_ATTRS or key.startswith("_"):
                continue
            if value is None:
                continue
            extras[key] = self._normalize_value(value)
        return extras

    @staticmethod
    def _normalize_value(value: object) -> object:
        if isinstance(value, (str, int, float, bool)):
            return value
        if value is None:
            return None
        if isinstance(value, (list, dict)):
            try:
                json.dumps(value)
                return value
            except TypeError:
                return str(value)
        return str(value)


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

    # Suppress noisy SQLAlchemy loggers
    logging.getLogger("sqlalchemy.engine").setLevel(logging.WARNING)
    logging.getLogger("sqlalchemy.pool").setLevel(logging.WARNING)
    logging.getLogger("sqlalchemy.dialects").setLevel(logging.WARNING)

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
