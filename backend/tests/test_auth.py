"""Tests for authentication flow (Telegram initData + JWT)."""

from __future__ import annotations

import hashlib
import hmac
import json
import time
from typing import Dict
from urllib.parse import parse_qsl, urlencode

import pytest
from fastapi.security import HTTPAuthorizationCredentials
from fastapi.testclient import TestClient

from app.api.dependencies.auth import get_current_user
from app.core.config import settings
from app.main import app
from app.repositories.user_repository import user_repository
from app.services.auth_service import get_auth_service

client = TestClient(app)

TEST_BOT_TOKEN = "999999:TEST_TOKEN"
TEST_SECRET_KEY = "test-secret-key"


@pytest.fixture(autouse=True)
def configure_environment():
    """Ensure deterministic settings for tests and reset repository state."""

    original_bot_token = settings.TELEGRAM_BOT_TOKEN
    original_secret_key = settings.SECRET_KEY
    original_security_headers = settings.SECURITY_HEADERS_ENABLED

    settings.TELEGRAM_BOT_TOKEN = TEST_BOT_TOKEN
    settings.SECRET_KEY = TEST_SECRET_KEY
    settings.SECURITY_HEADERS_ENABLED = True
    user_repository.reset()

    yield

    settings.TELEGRAM_BOT_TOKEN = original_bot_token
    settings.SECRET_KEY = original_secret_key
    settings.SECURITY_HEADERS_ENABLED = original_security_headers
    user_repository.reset()


def _generate_init_data(bot_token: str, overrides: Dict[str, str] | None = None) -> str:
    payload = {
        "query_id": "test-query",
        "user": json.dumps({
            "id": 123456,
            "first_name": "John",
            "last_name": "Doe",
            "username": "john_doe",
        }, separators=(",", ":")),
        "auth_date": str(int(time.time())),
    }
    if overrides:
        payload.update(overrides)

    data_check_string = "\n".join(f"{k}={v}" for k, v in sorted(payload.items()))
    secret_key = hmac.new(
        key="WebAppData".encode(),
        msg=bot_token.encode(),
        digestmod=hashlib.sha256,
    ).digest()
    hash_value = hmac.new(
        key=secret_key,
        msg=data_check_string.encode(),
        digestmod=hashlib.sha256,
    ).hexdigest()
    payload["hash"] = hash_value
    return urlencode(payload)


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
    init_data = _generate_init_data(TEST_BOT_TOKEN)
    response = client.post("/api/auth/validate", json={"init_data": init_data})

    assert response.status_code == 200
    data = response.json()
    assert data["user"]["telegram_id"] == 123456
    assert data["token"]
    assert data["expires_at"]


def test_validate_auth_endpoint_invalid_hash():
    init_data = _generate_init_data(TEST_BOT_TOKEN)
    parsed = dict(parse_qsl(init_data))
    parsed["hash"] = "deadbeef"
    tampered = urlencode(parsed)

    response = client.post("/api/auth/validate", json={"init_data": tampered})

    assert response.status_code == 401
    detail = response.json()["detail"]
    assert detail["code"] == "AUTH_FAILED"


@pytest.mark.asyncio
async def test_get_current_user_dependency_returns_user():
    init_data = _generate_init_data(TEST_BOT_TOKEN)
    token_response = client.post("/api/auth/validate", json={"init_data": init_data})
    assert token_response.status_code == 200
    token = token_response.json()["token"]

    credentials = HTTPAuthorizationCredentials(scheme="Bearer", credentials=token)
    auth_service = get_auth_service()

    user = await get_current_user(credentials, auth_service)

    assert user.telegram_id == 123456
