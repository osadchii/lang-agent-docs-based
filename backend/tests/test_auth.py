"""Tests for authentication flow (Telegram initData + JWT)."""

from __future__ import annotations

from urllib.parse import parse_qsl, urlencode

import pytest
from fastapi.security import HTTPAuthorizationCredentials
from fastapi.testclient import TestClient

from app.api.dependencies.auth import get_current_user
from app.main import app
from app.services.auth_service import get_auth_service
from tests.helpers import TEST_BOT_TOKEN, TEST_SECRET_KEY, generate_init_data

client = TestClient(app)


def test_security_headers_present_on_health_endpoint():
    response = client.get("/api/health")
    assert response.status_code == 200
    headers = response.headers
    assert headers["X-Content-Type-Options"] == "nosniff"
    assert headers["X-Frame-Options"] == "DENY"
    assert headers["X-XSS-Protection"] == "1; mode=block"
    assert "Content-Security-Policy" in headers
    assert "Permissions-Policy" in headers


def test_validate_auth_endpoint_success():
    init_data = generate_init_data(TEST_BOT_TOKEN)
    response = client.post("/api/auth/validate", json={"init_data": init_data})

    assert response.status_code == 200
    data = response.json()
    assert data["user"]["telegram_id"] == 123456
    assert data["token"]
    assert data["expires_at"]


def test_validate_auth_endpoint_invalid_hash():
    init_data = generate_init_data(TEST_BOT_TOKEN)
    parsed = dict(parse_qsl(init_data))
    parsed["hash"] = "deadbeef"
    tampered = urlencode(parsed)

    response = client.post("/api/auth/validate", json={"init_data": tampered})

    assert response.status_code == 401
    detail = response.json()["detail"]
    assert detail["code"] == "AUTH_FAILED"


@pytest.mark.asyncio
async def test_get_current_user_dependency_returns_user():
    init_data = generate_init_data(TEST_BOT_TOKEN)
    token_response = client.post("/api/auth/validate", json={"init_data": init_data})
    assert token_response.status_code == 200
    token = token_response.json()["token"]

    credentials = HTTPAuthorizationCredentials(scheme="Bearer", credentials=token)
    auth_service = get_auth_service()

    user = await get_current_user(credentials, auth_service)

    assert user.telegram_id == 123456
