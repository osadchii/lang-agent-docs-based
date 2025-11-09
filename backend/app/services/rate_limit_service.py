"""
Rate limiting utilities backed by Redis.

Implements the limits described in docs/backend-auth.md and
docs/backend-subscriptions.md:
- Global per-IP and per-user request caps
- Per-user daily limits for LLM usage and exercises
- Card creation limits for free plans
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from enum import Enum
from typing import Any, Callable, Dict, Optional, Protocol
from uuid import UUID

from redis.exceptions import RedisError

from app.core.logging import get_logger
from app.core.redis import RedisManager, redis_manager
from app.models.user import User

logger = get_logger(__name__)


class RateLimitAction(str, Enum):
    """Supported rate limit actions."""

    GLOBAL_IP = "global_ip"
    GLOBAL_USER = "global_user"
    LLM_MESSAGES = "llm_messages"
    EXERCISES = "exercises"
    CARD_CAP = "cards"


@dataclass(frozen=True)
class RateLimitRule:
    """Configuration for a single limit."""

    limit: Optional[int]
    window_seconds: int


@dataclass(frozen=True)
class LimitProfile:
    """Plan-specific limits."""

    llm_messages_per_day: Optional[int]
    exercises_per_day: Optional[int]
    max_cards_total: Optional[int]


FREE_PLAN_LIMITS = LimitProfile(
    llm_messages_per_day=50,
    exercises_per_day=10,
    max_cards_total=200,
)

PREMIUM_PLAN_LIMITS = LimitProfile(
    llm_messages_per_day=500,
    exercises_per_day=None,
    max_cards_total=None,
)

GLOBAL_IP_RULE = RateLimitRule(limit=100, window_seconds=60)  # 100 req/min
GLOBAL_USER_RULE = RateLimitRule(limit=1000, window_seconds=3600)  # 1000 req/hour
DAY_SECONDS = 24 * 60 * 60


@dataclass
class RateLimitResult:
    """Result of a rate limit check."""

    scope: str
    allowed: bool
    limit: Optional[int]
    remaining: Optional[int]
    reset_at: Optional[datetime]
    retry_after: Optional[int]

    def headers(self) -> Dict[str, str]:
        """Return standard X-RateLimit headers."""

        headers: Dict[str, str] = {}
        if self.limit is not None:
            headers["X-RateLimit-Limit"] = str(self.limit)
        if self.remaining is not None:
            headers["X-RateLimit-Remaining"] = str(max(self.remaining, 0))
        if self.reset_at is not None:
            headers["X-RateLimit-Reset"] = str(int(self.reset_at.timestamp()))
        if self.retry_after is not None:
            headers["Retry-After"] = str(self.retry_after)
        return headers

    @classmethod
    def unlimited(cls, scope: str) -> "RateLimitResult":
        """Return a result representing no active limit for the scope."""

        return cls(
            scope=scope,
            allowed=True,
            limit=None,
            remaining=None,
            reset_at=None,
            retry_after=None,
        )


@dataclass
class RateLimitCounterState:
    """Internal counter state (value + TTL)."""

    count: int
    ttl: int


class RateLimitCounter(Protocol):
    """Protocol for the underlying counter backend."""

    async def increment(self, key: str, window_seconds: int) -> RateLimitCounterState:
        ...


class RedisRateLimitCounter:
    """Redis-backed implementation of rate limit counters."""

    def __init__(self, manager: RedisManager) -> None:
        self._manager = manager

    async def increment(self, key: str, window_seconds: int) -> RateLimitCounterState:
        client = await self._manager.get_client()
        count = await client.incr(key)
        if count == 1:
            await client.expire(key, window_seconds)

        ttl = await client.ttl(key)
        if ttl < 0:
            await client.expire(key, window_seconds)
            ttl = window_seconds

        return RateLimitCounterState(count=count, ttl=int(ttl))


class InMemoryRateLimitCounter:
    """
    Simple in-memory counter used in tests.

    Not intended for production use.
    """

    def __init__(self) -> None:
        self._store: Dict[str, tuple[int, datetime]] = {}

    async def increment(self, key: str, window_seconds: int) -> RateLimitCounterState:
        now = datetime.now(timezone.utc)
        count, expires_at = self._store.get(key, (0, now))

        if expires_at <= now:
            count = 0
            expires_at = now + timedelta(seconds=window_seconds)

        count += 1
        self._store[key] = (count, expires_at)
        ttl = max(int((expires_at - now).total_seconds()), 0)
        return RateLimitCounterState(count=count, ttl=ttl)


class RateLimitExceededError(Exception):
    """Raised when a rate limit has been reached."""

    def __init__(
        self,
        *,
        scope: str,
        message: str,
        result: RateLimitResult,
        details: Optional[Dict[str, Any]] = None,
        error_code: str = "RATE_LIMIT_EXCEEDED",
    ) -> None:
        super().__init__(message)
        self.scope = scope
        self.message = message
        self.result = result
        self.details = details or {}
        self.error_code = error_code


class RateLimitService:
    """High-level rate limit checks for different actions."""

    def __init__(
        self,
        *,
        counter: RateLimitCounter,
        key_builder: Optional[Callable[..., str]] = None,
    ) -> None:
        self._counter = counter
        self._key_builder = key_builder or self._default_key_builder

    async def enforce_global_ip_limit(self, ip_address: str) -> RateLimitResult:
        """Apply per-IP throttle (100 req/min)."""

        key = self._key("ip", ip_address)
        return await self._enforce_rule(
            scope=RateLimitAction.GLOBAL_IP.value,
            key=key,
            rule=GLOBAL_IP_RULE,
            message="Слишком много запросов с этого IP. Попробуйте позже.",
        )

    async def enforce_global_user_limit(self, user_id: UUID) -> RateLimitResult:
        """Apply per-user throttle (1000 req/hour)."""

        key = self._key("user", str(user_id))
        return await self._enforce_rule(
            scope=RateLimitAction.GLOBAL_USER.value,
            key=key,
            rule=GLOBAL_USER_RULE,
            message="Слишком много запросов с этого пользователя. Попробуйте позже.",
        )

    async def ensure_llm_quota(self, user: User) -> RateLimitResult:
        """Ensure the user has spare LLM message quota."""

        profile = self._limit_profile_for_user(user)
        limit = profile.llm_messages_per_day
        return await self._enforce_daily_user_rule(
            user_id=user.id,
            action=RateLimitAction.LLM_MESSAGES,
            limit=limit,
            message="Достигнут дневной лимит сообщений. Обновите план или подождите до завтра.",
            details={"limit_type": "llm_messages", "max": limit},
        )

    async def ensure_exercise_quota(self, user: User) -> RateLimitResult:
        """Ensure the user can request another exercise."""

        profile = self._limit_profile_for_user(user)
        limit = profile.exercises_per_day
        return await self._enforce_daily_user_rule(
            user_id=user.id,
            action=RateLimitAction.EXERCISES,
            limit=limit,
            message="Достигнут дневной лимит упражнений. Попробуйте завтра или оформите премиум.",
            details={"limit_type": "exercises", "max": limit},
        )

    def ensure_card_quota(self, user: User, current_total_cards: int) -> RateLimitResult:
        """Validate total card cap for free plans."""

        profile = self._limit_profile_for_user(user)
        limit = profile.max_cards_total
        scope = RateLimitAction.CARD_CAP.value

        if limit is None:
            return RateLimitResult.unlimited(scope)

        remaining = max(limit - current_total_cards, 0)
        result = RateLimitResult(
            scope=scope,
            allowed=remaining > 0,
            limit=limit,
            remaining=remaining,
            reset_at=None,
            retry_after=None,
        )

        if remaining > 0:
            return result

        raise RateLimitExceededError(
            scope=scope,
            message="Достигнут лимит карточек для бесплатного плана.",
            result=result,
            details={
                "limit_type": "cards",
                "max": limit,
                "current": current_total_cards,
                "upgrade_url": "/profile/premium",
            },
            error_code="LIMIT_REACHED",
        )

    async def _enforce_daily_user_rule(
        self,
        *,
        user_id: UUID,
        action: RateLimitAction,
        limit: Optional[int],
        message: str,
        details: Optional[Dict[str, Any]] = None,
    ) -> RateLimitResult:
        date_suffix = datetime.now(timezone.utc).strftime("%Y%m%d")
        key = self._key("daily", str(user_id), action.value, date_suffix)
        return await self._enforce_rule(
            scope=action.value,
            key=key,
            rule=RateLimitRule(limit=limit, window_seconds=DAY_SECONDS),
            message=message,
            details=details,
        )

    async def _enforce_rule(
        self,
        *,
        scope: str,
        key: str,
        rule: RateLimitRule,
        message: str,
        details: Optional[Dict[str, Any]] = None,
    ) -> RateLimitResult:
        if rule.limit is None:
            return RateLimitResult.unlimited(scope)

        now = datetime.now(timezone.utc)
        try:
            state = await self._counter.increment(key, rule.window_seconds)
        except RedisError as exc:  # pragma: no cover - network failure
            logger.warning("Rate limit storage unavailable: %s", exc)
            return RateLimitResult.unlimited(scope)

        remaining = max(rule.limit - state.count, 0)
        ttl = state.ttl if state.ttl > 0 else rule.window_seconds
        reset_at = now + timedelta(seconds=ttl)
        allowed = state.count <= rule.limit
        retry_after = ttl if not allowed else None

        result = RateLimitResult(
            scope=scope,
            allowed=allowed,
            limit=rule.limit,
            remaining=remaining,
            reset_at=reset_at,
            retry_after=retry_after,
        )

        if allowed:
            return result

        raise RateLimitExceededError(
            scope=scope,
            message=message if retry_after is None else f"{message} Повторите через {retry_after} секунд.",
            result=result,
            details=details,
        )

    def _limit_profile_for_user(self, user: User) -> LimitProfile:
        now = datetime.now(timezone.utc)
        if user.is_premium:
            return PREMIUM_PLAN_LIMITS
        if user.trial_ends_at and user.trial_ends_at > now:
            return PREMIUM_PLAN_LIMITS
        return FREE_PLAN_LIMITS

    def _key(self, *parts: str) -> str:
        return self._key_builder(*parts)

    @staticmethod
    def _default_key_builder(*parts: str) -> str:
        return ":".join(["ratelimit", *parts])


_rate_limit_service: Optional[RateLimitService] = None


def get_rate_limit_service() -> RateLimitService:
    """Return singleton rate limit service instance."""

    global _rate_limit_service
    if _rate_limit_service is None:
        counter = RedisRateLimitCounter(redis_manager)
        _rate_limit_service = RateLimitService(
            counter=counter,
            key_builder=redis_manager.make_key,
        )
    return _rate_limit_service


def override_rate_limit_service(service: Optional[RateLimitService]) -> None:
    """
    Override singleton rate limit service (primarily for tests).

    Pass None to reset to default Redis-backed implementation.
    """

    global _rate_limit_service
    _rate_limit_service = service

