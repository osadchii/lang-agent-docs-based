from __future__ import annotations

import uuid

import pytest

from app.core.cache import CacheClient
from app.core.errors import ApplicationError
from app.services.rate_limit import RateLimitConfig, RateLimitedAction, RateLimitService


class FakeRedis:
    """Minimal async Redis stub for rate limit tests."""

    def __init__(self) -> None:
        self.store: dict[str, int] = {}
        self.ttls: dict[str, int] = {}
        self.sets: dict[str, set[str]] = {}

    async def close(self) -> None:
        return None

    async def get(self, key: str) -> str | None:
        return None

    async def set(self, key: str, value: str) -> bool:
        self.store[key] = 1
        return True

    async def setex(self, key: str, ttl: int, value: str) -> bool:
        self.store[key] = 1
        self.ttls[key] = ttl
        return True

    async def delete(self, *keys: str) -> int:
        removed = 0
        for key in keys:
            if key in self.store:
                removed += 1
                del self.store[key]
            if key in self.ttls:
                del self.ttls[key]
        return removed

    async def exists(self, key: str) -> int:
        return int(key in self.store)

    async def expire(self, key: str, ttl: int) -> bool:
        self.ttls[key] = ttl
        return True

    async def ttl(self, key: str) -> int:
        return self.ttls.get(key, -1)

    async def incr(self, key: str) -> int:
        self.store[key] = self.store.get(key, 0) + 1
        return self.store[key]

    async def sadd(self, key: str, *members: str) -> int:
        bucket = self.sets.setdefault(key, set())
        added = 0
        for member in members:
            if member not in bucket:
                bucket.add(member)
                added += 1
        return added

    async def smembers(self, key: str) -> set[str]:
        return set(self.sets.get(key, set()))

    async def srem(self, key: str, *members: str) -> int:
        bucket = self.sets.get(key)
        if not bucket:
            return 0
        removed = 0
        for member in members:
            if member in bucket:
                bucket.remove(member)
                removed += 1
        return removed


def build_service(*, enabled: bool = True) -> RateLimitService:
    cache = CacheClient("redis://test")
    cache._redis = FakeRedis()  # type: ignore[attr-defined]
    config = RateLimitConfig(
        ip_limit_per_minute=2,
        user_limit_per_hour=3,
        free_llm_per_day=2,
        premium_llm_per_day=4,
        free_exercises_per_day=1,
        premium_exercises_per_day=None,
    )
    return RateLimitService(cache, config=config, enabled=enabled)


@pytest.mark.asyncio
async def test_ip_limit_blocks_after_threshold() -> None:
    service = build_service()
    result1 = await service.check_ip_limit("1.1.1.1")
    assert result1.allowed
    assert result1.remaining == 1

    result2 = await service.check_ip_limit("1.1.1.1")
    assert result2.allowed
    assert result2.remaining == 0
    blocked = await service.check_ip_limit("1.1.1.1")
    assert blocked.allowed is False
    assert blocked.retry_after is not None


@pytest.mark.asyncio
async def test_user_limit_enforced_per_hour() -> None:
    service = build_service()
    user_id = str(uuid.uuid4())
    await service.check_user_limit(user_id)
    await service.check_user_limit(user_id)
    await service.check_user_limit(user_id)
    blocked = await service.check_user_limit(user_id)
    assert blocked.allowed is False


@pytest.mark.asyncio
async def test_enforce_action_limit_free_plan() -> None:
    service = build_service()

    class DummyUser:
        def __init__(self) -> None:
            self.id = uuid.uuid4()
            self.is_premium = False

    user = DummyUser()
    await service.enforce_action_limit(user, RateLimitedAction.LLM_MESSAGES)
    await service.enforce_action_limit(user, RateLimitedAction.LLM_MESSAGES)
    with pytest.raises(ApplicationError):
        await service.enforce_action_limit(user, RateLimitedAction.LLM_MESSAGES)


@pytest.mark.asyncio
async def test_premium_exercises_unlimited() -> None:
    service = build_service()

    class DummyPremiumUser:
        def __init__(self) -> None:
            self.id = uuid.uuid4()
            self.is_premium = True

    user = DummyPremiumUser()
    result = await service.enforce_action_limit(user, RateLimitedAction.EXERCISES)
    assert result is None  # Unlimited for premium plan in config


@pytest.mark.asyncio
async def test_reset_daily_counters_clears_keys() -> None:
    service = build_service()

    class DummyUser:
        def __init__(self) -> None:
            self.id = uuid.uuid4()
            self.is_premium = False

    user = DummyUser()
    await service.enforce_action_limit(user, RateLimitedAction.LLM_MESSAGES)

    cleared = await service.reset_daily_counters()
    assert cleared >= 1


@pytest.mark.asyncio
async def test_reset_daily_counters_no_keys() -> None:
    service = build_service()
    cleared = await service.reset_daily_counters()
    assert cleared == 0


@pytest.mark.asyncio
async def test_ip_limit_returns_unlimited_result_when_disabled() -> None:
    service = build_service(enabled=False)
    result = await service.check_ip_limit("127.0.0.1")
    assert result.allowed
    assert result.remaining == service.config.ip_limit_per_minute


@pytest.mark.asyncio
async def test_enforce_action_limit_disabled_returns_none() -> None:
    service = build_service(enabled=False)

    class DummyUser:
        def __init__(self) -> None:
            self.id = uuid.uuid4()
            self.is_premium = False

    user = DummyUser()
    assert await service.enforce_action_limit(user, RateLimitedAction.EXERCISES) is None
