from __future__ import annotations

from datetime import datetime

import pytest
from httpx import AsyncClient

from app.core.version import APP_VERSION
from app.main import app


@pytest.mark.asyncio
async def test_health_returns_expected_payload() -> None:
    async with AsyncClient(app=app, base_url="http://testserver") as client:
        response = await client.get("/health")

    assert response.status_code == 200

    payload = response.json()
    assert payload["status"] == "healthy"
    assert payload["version"] == APP_VERSION
    assert set(payload["checks"]) == {"database", "redis", "openai", "stripe"}

    # Ensure timestamp is ISO-8601 parsable
    datetime.fromisoformat(payload["timestamp"])


@pytest.mark.asyncio
async def test_request_id_header_generated() -> None:
    async with AsyncClient(app=app, base_url="http://testserver") as client:
        response = await client.get("/health")

    request_id = response.headers.get("X-Request-ID")
    assert request_id
    assert len(request_id) >= 8


@pytest.mark.asyncio
async def test_request_id_header_preserved_from_client() -> None:
    desired_request_id = "test-request-id-123"
    async with AsyncClient(app=app, base_url="http://testserver") as client:
        response = await client.get("/health", headers={"X-Request-ID": desired_request_id})

    assert response.headers.get("X-Request-ID") == desired_request_id


@pytest.mark.asyncio
async def test_access_log_contains_request_metadata(caplog: pytest.LogCaptureFixture) -> None:
    caplog.set_level("INFO", logger="app.access")

    async with AsyncClient(app=app, base_url="http://testserver") as client:
        await client.get("/health")

    log_record = next(record for record in caplog.records if record.name == "app.access")

    assert getattr(log_record, "http_method", None) == "GET"
    assert getattr(log_record, "http_path", None) == "/health"
    assert getattr(log_record, "status_code", None) == 200
    assert isinstance(getattr(log_record, "duration_ms", None), float)


@pytest.mark.asyncio
async def test_cors_preflight_allows_telegram_origin() -> None:
    headers = {
        "Origin": "https://webapp.telegram.org",
        "Access-Control-Request-Method": "GET",
        "Access-Control-Request-Headers": "Authorization",
    }

    async with AsyncClient(app=app, base_url="http://testserver") as client:
        response = await client.options("/health", headers=headers)

    assert response.status_code == 200
    assert response.headers.get("access-control-allow-origin") == "https://webapp.telegram.org"


@pytest.mark.asyncio
async def test_cors_preflight_rejects_unknown_origin() -> None:
    headers = {
        "Origin": "https://malicious.example.com",
        "Access-Control-Request-Method": "GET",
        "Access-Control-Request-Headers": "Authorization",
    }

    async with AsyncClient(app=app, base_url="http://testserver") as client:
        response = await client.options("/health", headers=headers)

    assert response.status_code == 400


@pytest.mark.asyncio
async def test_unknown_route_returns_structured_error() -> None:
    async with AsyncClient(app=app, base_url="http://testserver") as client:
        response = await client.get("/non-existent")

    assert response.status_code == 404
    payload = response.json()
    assert payload["error"]["code"] == "NOT_FOUND"
    assert "message" in payload["error"]
