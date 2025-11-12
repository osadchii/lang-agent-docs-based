from __future__ import annotations

import pytest
from fastapi import FastAPI, status
from httpx import AsyncClient

from app.core.middleware import RequestSizeLimitMiddleware, SecurityHeadersMiddleware


@pytest.mark.asyncio
async def test_request_size_limit_rejects_large_payload() -> None:
    app = FastAPI()
    app.add_middleware(RequestSizeLimitMiddleware, max_request_bytes=64)

    @app.post("/echo")
    async def echo_endpoint() -> dict[str, str]:
        return {"status": "ok"}

    async with AsyncClient(app=app, base_url="http://testserver") as client:
        response = await client.post(
            "/echo", content="x" * 128, headers={"content-type": "text/plain"}
        )

    assert response.status_code == status.HTTP_413_REQUEST_ENTITY_TOO_LARGE
    payload = response.json()
    assert payload["error"]["code"] == "PAYLOAD_TOO_LARGE"
    assert payload["error"]["message"].startswith("Request body exceeds")


@pytest.mark.asyncio
async def test_request_size_limit_allows_small_payload() -> None:
    app = FastAPI()
    app.add_middleware(RequestSizeLimitMiddleware, max_request_bytes=256)

    @app.post("/echo")
    async def echo_endpoint() -> dict[str, str]:
        return {"status": "ok"}

    async with AsyncClient(app=app, base_url="http://testserver") as client:
        response = await client.post("/echo", json={"message": "ok"})

    assert response.status_code == status.HTTP_200_OK
    assert response.json() == {"status": "ok"}


@pytest.mark.asyncio
async def test_security_headers_middleware_injects_headers() -> None:
    app = FastAPI()
    app.add_middleware(SecurityHeadersMiddleware, enable_hsts=True)

    @app.get("/ping")
    async def ping() -> dict[str, str]:
        return {"status": "ok"}

    async with AsyncClient(app=app, base_url="http://testserver") as client:
        response = await client.get("/ping")

    headers = response.headers
    assert headers["X-Content-Type-Options"] == "nosniff"
    assert headers["X-Frame-Options"] == "DENY"
    assert headers["Referrer-Policy"] == "same-origin"
    assert headers["Permissions-Policy"] == "camera=(), microphone=()"
    assert headers["Strict-Transport-Security"].startswith("max-age=")
