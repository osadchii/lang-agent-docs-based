"""Tests for rate limiting service and middleware."""

from __future__ import annotations

from datetime import datetime, timezone
from uuid import uuid4

import pytest
from fastapi.testclient import TestClient

from app.main import app
from app.models.user import User
from app.services.rate_limit_service import (
    InMemoryRateLimitCounter,
    RateLimitExceededError,
    RateLimitService,
    override_rate_limit_service,
)


@pytest.fixture
def rate_limit_service():
    """Provide a rate limit service backed by in-memory counters."""

    service = RateLimitService(counter=InMemoryRateLimitCounter())
    return service


@pytest.fixture(autouse=True)
def override_service(rate_limit_service):
    """
    Override the global rate limit service for each test.

    Ensures deterministic behaviour without Redis.
    """

    override_rate_limit_service(rate_limit_service)
    yield
    override_rate_limit_service(None)


def _make_user(is_premium: bool = False) -> User:
    """Helper to create user objects for tests."""

    return User(
        id=uuid4(),
        telegram_id=123456,
        first_name="Test",
        last_name="User",
        username="test_user",
        is_premium=is_premium,
        created_at=datetime.now(timezone.utc),
    )


@pytest.mark.asyncio
async def test_llm_quota_enforced_for_free_users(rate_limit_service: RateLimitService):
    user = _make_user(is_premium=False)

    for _ in range(50):
        result = await rate_limit_service.ensure_llm_quota(user)
        assert result.allowed

    with pytest.raises(RateLimitExceededError):
        await rate_limit_service.ensure_llm_quota(user)


@pytest.mark.asyncio
async def test_exercise_quota_blocks_after_limit(rate_limit_service: RateLimitService):
    user = _make_user(is_premium=False)

    for _ in range(10):
        result = await rate_limit_service.ensure_exercise_quota(user)
        assert result.allowed

    with pytest.raises(RateLimitExceededError):
        await rate_limit_service.ensure_exercise_quota(user)


@pytest.mark.asyncio
async def test_premium_users_have_higher_llm_limit(rate_limit_service: RateLimitService):
    user = _make_user(is_premium=True)

    for _ in range(120):
        result = await rate_limit_service.ensure_llm_quota(user)
        assert result.allowed


def test_card_quota_enforced_for_free_plan(rate_limit_service: RateLimitService):
    user = _make_user(is_premium=False)

    with pytest.raises(RateLimitExceededError):
        rate_limit_service.ensure_card_quota(user, current_total_cards=200)


def test_card_quota_unlimited_for_premium(rate_limit_service: RateLimitService):
    user = _make_user(is_premium=True)

    result = rate_limit_service.ensure_card_quota(user, current_total_cards=5_000)
    assert result.allowed
    assert result.limit is None


def test_global_ip_rate_limit_returns_429_when_exceeded():
    with TestClient(app) as client:
        for _ in range(100):
            response = client.get("/api/health")
            assert response.status_code == 200

        response = client.get("/api/health")

    assert response.status_code == 429
    data = response.json()
    assert data["error"]["code"] == "RATE_LIMIT_EXCEEDED"
    assert "retry_after" in data["error"]
    assert response.headers["X-RateLimit-Limit"] == "100"
    assert response.headers["X-RateLimit-Remaining"] == "0"
