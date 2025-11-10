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
