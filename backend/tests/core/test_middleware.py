from __future__ import annotations

import time

import pytest
from fastapi import FastAPI, status
from httpx import AsyncClient

from app.core.middleware import (
    RateLimitMiddleware,
    RequestSizeLimitMiddleware,
    SecurityHeadersMiddleware,
)
from app.services.rate_limit import RateLimitResult, RateLimitScope


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


def _build_result(
    *,
    allowed: bool,
    scope: RateLimitScope,
    limit: int = 10,
    remaining: int = 5,
    retry_after: int | None = None,
) -> RateLimitResult:
    return RateLimitResult(
        key=f"{scope.value}:test",
        limit=limit,
        window_seconds=60,
        remaining=remaining,
        reset_timestamp=int(time.time()) + 60,
        retry_after=retry_after,
        allowed=allowed,
        scope=scope,
    )


class StubRateLimitService:
    def __init__(
        self,
        *,
        enabled: bool,
        ip_result: RateLimitResult,
        user_result: RateLimitResult | None = None,
    ) -> None:
        self.enabled = enabled
        self.ip_result = ip_result
        self.user_result = user_result
        self.ip_calls = 0
        self.user_calls = 0

    async def check_ip_limit(self, client_ip: str) -> RateLimitResult:
        self.ip_calls += 1
        return self.ip_result

    async def check_user_limit(self, user_id: str) -> RateLimitResult:
        self.user_calls += 1
        if self.user_result is None:
            raise AssertionError("User limit called unexpectedly")
        return self.user_result


@pytest.mark.asyncio
async def test_rate_limit_middleware_bypasses_when_disabled() -> None:
    service = StubRateLimitService(
        enabled=False,
        ip_result=_build_result(allowed=True, scope=RateLimitScope.IP),
    )
    app = FastAPI()
    app.add_middleware(RateLimitMiddleware, service=service)

    @app.get("/ping")
    async def ping() -> dict[str, str]:
        return {"status": "ok"}

    async with AsyncClient(app=app, base_url="http://testserver") as client:
        response = await client.get("/ping")

    assert response.status_code == 200
    assert service.ip_calls == 0


@pytest.mark.asyncio
async def test_rate_limit_middleware_blocks_when_ip_limit_exceeded() -> None:
    service = StubRateLimitService(
        enabled=True,
        ip_result=_build_result(
            allowed=False,
            scope=RateLimitScope.IP,
            retry_after=3,
            remaining=0,
        ),
    )
    app = FastAPI()
    app.add_middleware(RateLimitMiddleware, service=service)

    @app.get("/ping")
    async def ping() -> dict[str, str]:
        return {"status": "ok"}

    async with AsyncClient(app=app, base_url="http://testserver") as client:
        response = await client.get("/ping")

    assert response.status_code == status.HTTP_429_TOO_MANY_REQUESTS
    payload = response.json()
    assert payload["error"]["code"] == "RATE_LIMIT_EXCEEDED"
    assert response.headers["X-RateLimit-Limit"] == "10"


@pytest.mark.asyncio
async def test_rate_limit_middleware_blocks_on_user_limit(monkeypatch: pytest.MonkeyPatch) -> None:
    service = StubRateLimitService(
        enabled=True,
        ip_result=_build_result(allowed=True, scope=RateLimitScope.IP),
        user_result=_build_result(
            allowed=False,
            scope=RateLimitScope.USER,
            retry_after=7,
            limit=1000,
            remaining=0,
        ),
    )
    app = FastAPI()
    app.add_middleware(RateLimitMiddleware, service=service)

    @app.get("/ping")
    async def ping() -> dict[str, str]:
        return {"status": "ok"}

    monkeypatch.setattr(
        "app.core.middleware.decode_access_token",
        lambda token: {"user_id": "123"},
    )

    async with AsyncClient(app=app, base_url="http://testserver") as client:
        response = await client.get("/ping", headers={"Authorization": "Bearer test"})

    assert response.status_code == status.HTTP_429_TOO_MANY_REQUESTS
    assert response.headers["Retry-After"] == "7"
    assert service.user_calls == 1


@pytest.mark.asyncio
async def test_rate_limit_middleware_sets_headers_from_user_scope(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    service = StubRateLimitService(
        enabled=True,
        ip_result=_build_result(allowed=True, scope=RateLimitScope.IP, limit=50, remaining=49),
        user_result=_build_result(
            allowed=True,
            scope=RateLimitScope.USER,
            limit=1000,
            remaining=999,
        ),
    )
    app = FastAPI()
    app.add_middleware(RateLimitMiddleware, service=service)

    @app.get("/ping")
    async def ping() -> dict[str, str]:
        return {"status": "ok"}

    monkeypatch.setattr(
        "app.core.middleware.decode_access_token",
        lambda token: {"user_id": "user-42"},
    )

    async with AsyncClient(app=app, base_url="http://testserver") as client:
        response = await client.get("/ping", headers={"Authorization": "Bearer ok"})

    assert response.status_code == status.HTTP_200_OK
    assert response.headers["X-RateLimit-Limit"] == "1000"
    assert response.headers["X-RateLimit-Remaining"] == "999"
