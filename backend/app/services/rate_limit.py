"""Redis-backed rate limiting service for API and domain quotas."""

from __future__ import annotations

import logging
import time
from dataclasses import dataclass
from enum import StrEnum
from typing import Iterable, cast

from fastapi import Response, status

from app.core.cache import CacheClient, RedisConnection
from app.core.config import settings
from app.core.errors import ApplicationError, ErrorCode
from app.models.user import User

logger = logging.getLogger("app.services.rate_limit")

DAILY_INDEX_KEY = "ratelimit:daily:index"
ONE_MINUTE = 60
ONE_HOUR = 3600
ONE_DAY = 86400


class RateLimitScope(StrEnum):
    """Known scopes for rate limit counters."""

    IP = "ip"
    USER = "user"
    ACTION = "action"


class RateLimitedAction(StrEnum):
    """Feature-specific counters that use day-long windows."""

    LLM_MESSAGES = "llm_messages"
    EXERCISES = "exercise_generation"


@dataclass(slots=True)
class RateLimitResult:
    """Outcome of a rate limit check."""

    key: str
    limit: int
    window_seconds: int
    remaining: int
    reset_timestamp: int
    retry_after: int | None
    allowed: bool
    scope: RateLimitScope

    def headers(self) -> dict[str, str]:
        """Return standard X-RateLimit-* headers."""
        return {
            "X-RateLimit-Limit": str(self.limit),
            "X-RateLimit-Remaining": str(max(0, self.remaining)),
            "X-RateLimit-Reset": str(self.reset_timestamp),
        }

    def apply(self, response: Response) -> None:
        """Attach rate limit headers to the outgoing response."""
        for header, value in self.headers().items():
            response.headers[header] = value
        if self.retry_after:
            response.headers.setdefault("Retry-After", str(self.retry_after))


@dataclass(slots=True)
class ActionLimit:
    """Plan-specific limits for a feature."""

    window_seconds: int
    free_limit: int | None
    premium_limit: int | None


@dataclass(slots=True)
class RateLimitConfig:
    """Configuration bundle describing all limits."""

    ip_limit_per_minute: int = 100
    user_limit_per_hour: int = 1000
    free_llm_per_day: int = 50
    premium_llm_per_day: int = 500
    free_exercises_per_day: int = 10
    premium_exercises_per_day: int | None = None

    @classmethod
    def from_settings(cls) -> RateLimitConfig:
        """Build configuration from app settings."""
        premium_exercises = settings.rate_limit_premium_exercises_per_day
        premium_exercises_limit = (
            None if premium_exercises is None or premium_exercises <= 0 else premium_exercises
        )
        return cls(
            ip_limit_per_minute=settings.rate_limit_ip_per_minute,
            user_limit_per_hour=settings.rate_limit_user_per_hour,
            free_llm_per_day=settings.rate_limit_free_llm_per_day,
            premium_llm_per_day=settings.rate_limit_premium_llm_per_day,
            free_exercises_per_day=settings.rate_limit_free_exercises_per_day,
            premium_exercises_per_day=premium_exercises_limit,
        )


class RateLimitService:
    """Orchestrates Redis counters for rate limiting."""

    def __init__(
        self,
        cache: CacheClient,
        config: RateLimitConfig | None = None,
        *,
        enabled: bool = True,
    ) -> None:
        self.cache = cache
        self.config = config or RateLimitConfig.from_settings()
        self.enabled = enabled
        self.action_limits: dict[RateLimitedAction, ActionLimit] = {
            RateLimitedAction.LLM_MESSAGES: ActionLimit(
                window_seconds=ONE_DAY,
                free_limit=self._normalize_limit(self.config.free_llm_per_day),
                premium_limit=self._normalize_limit(self.config.premium_llm_per_day),
            ),
            RateLimitedAction.EXERCISES: ActionLimit(
                window_seconds=ONE_DAY,
                free_limit=self._normalize_limit(self.config.free_exercises_per_day),
                premium_limit=self._normalize_limit(self.config.premium_exercises_per_day),
            ),
        }

    async def check_ip_limit(self, client_ip: str) -> RateLimitResult:
        """Increment and evaluate the per-IP limit."""
        limit = self.config.ip_limit_per_minute
        if limit <= 0:
            raise ValueError("rate_limit_ip_per_minute must be greater than zero.")
        if not self.enabled:
            return self._disabled_result(
                key=f"ratelimit:ip:{client_ip}",
                limit=limit,
                window_seconds=ONE_MINUTE,
                scope=RateLimitScope.IP,
            )
        return await self._check_limit(
            key=f"ratelimit:ip:{client_ip}",
            limit=limit,
            window_seconds=ONE_MINUTE,
            scope=RateLimitScope.IP,
        )

    async def check_user_limit(self, user_id: str) -> RateLimitResult:
        """Increment and evaluate the per-user hourly request limit."""
        limit = self.config.user_limit_per_hour
        if limit <= 0:
            raise ValueError("rate_limit_user_per_hour must be greater than zero.")
        if not self.enabled:
            return self._disabled_result(
                key=f"ratelimit:user:{user_id}",
                limit=limit,
                window_seconds=ONE_HOUR,
                scope=RateLimitScope.USER,
            )
        return await self._check_limit(
            key=f"ratelimit:user:{user_id}",
            limit=limit,
            window_seconds=ONE_HOUR,
            scope=RateLimitScope.USER,
        )

    async def enforce_action_limit(
        self,
        user: User,
        action: RateLimitedAction,
    ) -> RateLimitResult | None:
        """Enforce daily limits for feature-specific actions."""
        if not self.enabled:
            return None
        plan_limit = self._plan_limit(user, action)
        if plan_limit is None:
            return None

        config = self.action_limits[action]
        result = await self._check_limit(
            key=f"ratelimit:action:{action.value}:{user.id}",
            limit=plan_limit,
            window_seconds=config.window_seconds,
            scope=RateLimitScope.ACTION,
            track_daily=True,
        )
        if not result.allowed:
            message = self._action_error_message(action, plan_limit)
            raise ApplicationError(
                code=ErrorCode.RATE_LIMIT_EXCEEDED,
                message=message,
                status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                retry_after=result.retry_after,
                details={"action": action.value, "limit": plan_limit},
            )
        return result

    async def reset_daily_counters(self) -> int:
        """Clear tracked day-long counters (used by the scheduler)."""
        redis = await self._redis()
        members: list[str] = list(await redis.smembers(DAILY_INDEX_KEY))
        if not members:
            return 0

        removed = 0
        for chunk in _chunked(members, size=256):
            removed += await redis.delete(*chunk)
            await redis.srem(DAILY_INDEX_KEY, *chunk)

        if removed:
            logger.info("Reset daily rate limit counters", extra={"removed": removed})
        return removed

    async def _check_limit(
        self,
        *,
        key: str,
        limit: int,
        window_seconds: int,
        scope: RateLimitScope,
        track_daily: bool = False,
    ) -> RateLimitResult:
        redis = await self._redis()
        current = await redis.incr(key)
        ttl = await redis.ttl(key)
        if ttl < 0:
            await redis.expire(key, window_seconds)
            ttl = window_seconds
        if track_daily:
            await redis.sadd(DAILY_INDEX_KEY, key)

        allowed = current <= limit
        remaining = max(0, limit - current)
        reset_timestamp = int(time.time()) + ttl
        retry_after = ttl if not allowed else None
        return RateLimitResult(
            key=key,
            limit=limit,
            window_seconds=window_seconds,
            remaining=remaining,
            reset_timestamp=reset_timestamp,
            retry_after=retry_after,
            allowed=allowed,
            scope=scope,
        )

    async def _redis(self) -> RedisConnection:
        await self.cache.connect()
        return self.cache.redis

    def _plan_limit(self, user: User, action: RateLimitedAction) -> int | None:
        limits = self.action_limits[action]
        is_premium = cast(bool, getattr(user, "is_premium", False))
        return limits.premium_limit if is_premium else limits.free_limit

    @staticmethod
    def _normalize_limit(value: int | None) -> int | None:
        if value is None:
            return None
        return value if value > 0 else None

    @staticmethod
    def _disabled_result(
        *,
        key: str,
        limit: int,
        window_seconds: int,
        scope: RateLimitScope,
    ) -> RateLimitResult:
        now = int(time.time())
        return RateLimitResult(
            key=key,
            limit=limit,
            window_seconds=window_seconds,
            remaining=limit,
            reset_timestamp=now + window_seconds,
            retry_after=None,
            allowed=True,
            scope=scope,
        )

    @staticmethod
    def _action_error_message(action: RateLimitedAction, limit: int) -> str:
        if action is RateLimitedAction.LLM_MESSAGES:
            return f"Daily dialog quota reached ({limit} messages)."
        if action is RateLimitedAction.EXERCISES:
            return f"Daily exercise generation quota reached ({limit} exercises)."
        return "Daily limit reached."


def _chunked(sequence: Iterable[str], *, size: int) -> Iterable[list[str]]:
    """Yield lists with up to `size` entries from a sequence."""
    chunk: list[str] = []
    for item in sequence:
        chunk.append(item)
        if len(chunk) >= size:
            yield chunk
            chunk = []
    if chunk:
        yield chunk


rate_limit_cache = CacheClient(settings.redis_url)
rate_limit_service = RateLimitService(
    rate_limit_cache,
    enabled=settings.environment != "test",
)

__all__ = [
    "ActionLimit",
    "RateLimitConfig",
    "RateLimitResult",
    "RateLimitScope",
    "RateLimitService",
    "RateLimitedAction",
    "rate_limit_service",
]
