from __future__ import annotations

import json
import logging
from types import ModuleType

import pytest

from app.core import logging as logging_module


@pytest.fixture()
def fresh_logging_module(monkeypatch: pytest.MonkeyPatch) -> ModuleType:
    root_logger = logging.getLogger()
    original_handlers = root_logger.handlers[:]
    original_level = root_logger.level

    monkeypatch.setattr(logging_module, "_LOGGING_CONFIGURED", False)

    yield logging_module

    root_logger.handlers = original_handlers
    root_logger.setLevel(original_level)
    logging_module._LOGGING_CONFIGURED = False


def test_configure_logging_installs_json_formatter(fresh_logging_module: ModuleType) -> None:
    fresh_logging_module.configure_logging("debug")

    root_logger = logging.getLogger()
    assert root_logger.level == logging.DEBUG
    assert any(
        isinstance(handler.formatter, logging_module.JsonLogFormatter)
        for handler in root_logger.handlers
    )


def test_configure_logging_is_idempotent(fresh_logging_module: ModuleType) -> None:
    fresh_logging_module.configure_logging("info")
    root_logger = logging.getLogger()
    first_handlers = list(root_logger.handlers)

    fresh_logging_module.configure_logging("warning")

    assert list(root_logger.handlers) == first_handlers
    assert root_logger.level == logging.INFO


def test_json_formatter_enriches_request_context(fresh_logging_module: ModuleType) -> None:
    token = logging_module.bind_request_id("req-123")
    logger = logging.getLogger("test-json")

    try:
        record = logger.makeRecord(
            name="test-json",
            level=logging.INFO,
            fn="test_logging.py",
            lno=42,
            msg="payload ready",
            args=(),
            exc_info=None,
            func="test_json_formatter_enriches_request_context",
            extra={
                "http_method": "GET",
                "http_path": "/health",
                "status_code": 200,
                "duration_ms": 12.5,
            },
        )
        formatted = logging_module.JsonLogFormatter().format(record)
    finally:
        logging_module.reset_request_id(token)

    payload = json.loads(formatted)
    assert payload["request_id"] == "req-123"
    assert payload["http_method"] == "GET"
    assert payload["http_path"] == "/health"
    assert payload["status_code"] == 200
    assert payload["duration_ms"] == 12.5


def test_json_formatter_includes_arbitrary_extra_fields(
    fresh_logging_module: ModuleType,
) -> None:
    logger = logging.getLogger("test-extra")
    record = logger.makeRecord(
        name="test-extra",
        level=logging.ERROR,
        fn="test_logging.py",
        lno=99,
        msg="whisper failed",
        args=(),
        exc_info=None,
        func="test_json_formatter_includes_arbitrary_extra_fields",
        extra={
            "openai_code": "file_invalid",
            "response_body": {"error": {"message": "bad audio"}},
            "non_serializable": object(),
        },
    )

    payload = json.loads(logging_module.JsonLogFormatter().format(record))

    assert payload["openai_code"] == "file_invalid"
    assert payload["response_body"] == {"error": {"message": "bad audio"}}
    assert isinstance(payload["non_serializable"], str)
