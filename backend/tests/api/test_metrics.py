from __future__ import annotations

import pytest
from httpx import AsyncClient

from app.main import app


@pytest.mark.asyncio
async def test_metrics_endpoint_exposes_request_metrics_with_request_id() -> None:
    async with AsyncClient(app=app, base_url="http://testserver") as client:
        request_id = "metrics-test-123"
        await client.get("/health", headers={"X-Request-ID": request_id})
        response = await client.get("/metrics")

    assert response.status_code == 200
    body = response.text
    assert "http_requests_total" in body
    assert 'handler="/health"' in body
    assert f'request_id="{request_id}"' in body
