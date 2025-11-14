"""
Redis cache utilities for LLM responses and other hot data.

Implements caching strategies with configurable TTLs according to data types:
- Translations and definitions: 30 days
- Generated flashcards: 30 days
- Lemmas (base forms): permanent (no TTL)
- Topic suggestions: 1 hour
"""

from __future__ import annotations

import hashlib
import json
import logging
from collections.abc import Awaitable, Coroutine
from functools import wraps
from typing import TYPE_CHECKING, Any, Callable, Protocol, TypeVar, cast

import redis.asyncio as aioredis

if TYPE_CHECKING:
    from typing_extensions import Self

logger = logging.getLogger("app.core.cache")

# Cache TTLs (Time To Live) in seconds
TTL_30_DAYS = 30 * 24 * 3600  # 2592000 seconds
TTL_1_HOUR = 3600
TTL_PERMANENT = None  # No expiration


T = TypeVar("T")


class PydanticModel(Protocol):
    """Protocol for Pydantic models with JSON validation."""

    @classmethod
    def model_validate_json(cls, json_data: str) -> Self:
        """Validate and parse JSON data into model instance."""
        ...

    def model_dump_json(self) -> str:
        """Serialize model to JSON string."""
        ...


class RedisConnection(Protocol):
    """Subset of redis.asyncio client operations used by the cache."""

    async def close(self) -> None: ...

    async def get(self, key: str) -> str | None: ...

    async def set(self, key: str, value: str) -> bool: ...

    async def setex(self, key: str, ttl: int, value: str) -> bool: ...

    async def delete(self, key: str) -> int: ...

    async def exists(self, key: str) -> int: ...


class CacheClient:
    """Async Redis cache client for LLM responses."""

    def __init__(self, redis_url: str) -> None:
        """
        Initialize cache client.

        Args:
            redis_url: Redis connection URL (redis://host:port/db)
        """
        self.redis_url = redis_url
        self._redis: RedisConnection | None = None
        logger.info("Cache client initialized", extra={"redis_url": redis_url})

    async def connect(self) -> None:
        """Establish connection to Redis."""
        if self._redis is None:
            redis_from_url = cast(Callable[..., Awaitable[RedisConnection]], aioredis.from_url)
            self._redis = await redis_from_url(
                self.redis_url, encoding="utf-8", decode_responses=True
            )
            logger.info("Connected to Redis")

    async def disconnect(self) -> None:
        """Close Redis connection."""
        if self._redis:
            await self._redis.close()
            self._redis = None
            logger.info("Disconnected from Redis")

    @property
    def redis(self) -> RedisConnection:
        """Get Redis client instance."""
        if self._redis is None:
            raise RuntimeError("Cache client not connected. Call connect() first.")
        return self._redis

    async def get(self, key: str) -> str | None:
        """
        Get value from cache.

        Args:
            key: Cache key

        Returns:
            Cached value or None if not found
        """
        try:
            value = await self.redis.get(key)
            if value:
                logger.debug("Cache hit", extra={"key": key})
            return value
        except Exception as e:
            logger.error("Cache get error", extra={"key": key, "error": str(e)})
            return None

    async def set(self, key: str, value: str, ttl: int | None = None) -> bool:
        """
        Set value in cache with optional TTL.

        Args:
            key: Cache key
            value: Value to cache
            ttl: Time to live in seconds (None for permanent)

        Returns:
            True if successful, False otherwise
        """
        try:
            if ttl:
                await self.redis.setex(key, ttl, value)
            else:
                await self.redis.set(key, value)
            logger.debug("Cache set", extra={"key": key, "ttl": ttl, "value_length": len(value)})
            return True
        except Exception as e:
            logger.error("Cache set error", extra={"key": key, "error": str(e)})
            return False

    async def delete(self, key: str) -> bool:
        """
        Delete value from cache.

        Args:
            key: Cache key

        Returns:
            True if key was deleted, False if key didn't exist or error occurred
        """
        try:
            result = await self.redis.delete(key)
            logger.debug("Cache delete", extra={"key": key, "deleted": bool(result)})
            return bool(result)
        except Exception as e:
            logger.error("Cache delete error", extra={"key": key, "error": str(e)})
            return False

    async def exists(self, key: str) -> bool:
        """
        Check if key exists in cache.

        Args:
            key: Cache key

        Returns:
            True if key exists, False otherwise
        """
        try:
            return bool(await self.redis.exists(key))
        except Exception as e:
            logger.error("Cache exists error", extra={"key": key, "error": str(e)})
            return False


# Cache key builders for different data types
def card_cache_key(language: str, lemma: str) -> str:
    """Generate cache key for flashcard content."""
    return f"card:{language}:{lemma.lower()}"


def lemma_cache_key(language: str, word: str) -> str:
    """Generate cache key for word lemma."""
    return f"lemma:{language}:{word.lower()}"


def translation_cache_key(source_lang: str, target_lang: str, word: str) -> str:
    """Generate cache key for translation."""
    return f"translation:{source_lang}:{target_lang}:{word.lower()}"


def topics_cache_key(profile_id: str) -> str:
    """Generate cache key for topic suggestions."""
    return f"topics:{profile_id}"


def generic_llm_cache_key(
    operation: str, **params: str | int | float | bool
) -> str:  # noqa: ANN401
    """
    Generate cache key for generic LLM operation.

    Args:
        operation: Operation name (e.g., 'generate_exercise', 'check_answer')
        **params: Parameters that uniquely identify the request

    Returns:
        Cache key string
    """
    # Sort params for consistent key generation
    sorted_params = sorted(params.items())
    param_str = json.dumps(sorted_params, sort_keys=True, ensure_ascii=False)
    # Hash params to keep key length reasonable
    param_hash = hashlib.md5(param_str.encode(), usedforsecurity=False).hexdigest()  # noqa: S324
    return f"llm:{operation}:{param_hash}"


def exercise_session_cache_key(exercise_id: str) -> str:
    """Cache key storing pending exercise data between requests."""
    return f"exercise_session:{exercise_id}"


def cache_llm_response(
    ttl: int | None,
    key_builder: Callable[..., str],
    model_class: type[PydanticModel] | None = None,
) -> Callable[[Callable[..., Awaitable[T]]], Callable[..., Coroutine[Any, Any, T]]]:
    """
    Decorator for caching LLM responses.

    Args:
        ttl: Time to live in seconds (None for permanent)
        key_builder: Function to build cache key from function arguments
        model_class: Optional Pydantic model class for deserialization.
                     If not provided, caching works but requires calling the function on cache hit.

    Returns:
        Decorated function with caching

    Example:
        @cache_llm_response(
            ttl=TTL_30_DAYS,
            key_builder=lambda lang, word: f"card:{lang}:{word}",
            model_class=CardContent
        )
        async def generate_card(language: str, word: str) -> CardContent:
            ...
    """

    def decorator(func: Callable[..., Awaitable[T]]) -> Callable[..., Coroutine[Any, Any, T]]:
        @wraps(func)
        async def wrapper(*args: Any, **kwargs: Any) -> T:  # noqa: ANN401
            # Extract cache client from first argument (usually self)
            if not args or not hasattr(args[0], "cache"):
                # If no cache client available, skip caching
                logger.debug(f"No cache client for {func.__name__}, executing without cache")
                return await func(*args, **kwargs)

            cache: CacheClient = args[0].cache

            # Build cache key
            try:
                # Try to extract relevant kwargs for key building
                cache_key = key_builder(**kwargs)
            except Exception as e:
                logger.warning(
                    f"Failed to build cache key for {func.__name__}: {e}, executing without cache"
                )
                return await func(*args, **kwargs)

            # Try to get from cache
            try:
                cached_value = await cache.get(cache_key)
                if cached_value and model_class:
                    logger.info(f"Cache hit for {func.__name__}", extra={"cache_key": cache_key})
                    # Parse JSON and return typed result using provided model class
                    return cast(T, model_class.model_validate_json(cached_value))
            except Exception as e:
                logger.warning(f"Cache read error for {func.__name__}: {e}")

            # Execute function
            result = await func(*args, **kwargs)

            # Cache result
            try:
                if hasattr(result, "model_dump_json"):
                    # Pydantic model
                    result_json = result.model_dump_json()
                else:
                    result_json = json.dumps(result)

                await cache.set(cache_key, result_json, ttl)
                logger.info(
                    f"Cached result for {func.__name__}",
                    extra={"cache_key": cache_key, "ttl": ttl},
                )
            except Exception as e:
                logger.error(f"Cache write error for {func.__name__}: {e}")

            return result

        return wrapper

    return decorator


__all__ = [
    "CacheClient",
    "TTL_30_DAYS",
    "TTL_1_HOUR",
    "TTL_PERMANENT",
    "card_cache_key",
    "lemma_cache_key",
    "translation_cache_key",
    "exercise_session_cache_key",
    "topics_cache_key",
    "generic_llm_cache_key",
    "cache_llm_response",
]
