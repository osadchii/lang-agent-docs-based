"""
Redis client manager.

Provides a single connection pool that can be reused across the
application and exposes helpers for generating namespaced keys.
The actual connection parameters are controlled via REDIS_URL
from the application settings (see docs/deployment.md).
"""

from __future__ import annotations

import asyncio
from typing import Optional

from redis.asyncio import Redis, from_url
from redis.exceptions import RedisError

from app.core.config import settings
from app.core.logging import get_logger

logger = get_logger(__name__)


class RedisManager:
    """Manage a shared Redis connection."""

    def __init__(self, url: str, namespace: str = "langagent") -> None:
        self._url = url
        self._namespace = namespace
        self._client: Optional[Redis] = None
        self._lock = asyncio.Lock()

    async def connect(self) -> None:
        """
        Establish a Redis connection if not connected yet.

        Called from FastAPI startup event. Safe to invoke multiple times.
        """

        if self._client is not None:
            return

        async with self._lock:
            if self._client is not None:
                return

            logger.info("Connecting to Redis at %s", self._url)
            client = from_url(
                self._url,
                encoding="utf-8",
                decode_responses=True,
                health_check_interval=30,
            )

            try:
                await client.ping()
            except RedisError as exc:
                logger.error("Failed to connect to Redis: %s", exc)
                raise

            self._client = client
            logger.info("Redis connection established")

    async def get_client(self) -> Redis:
        """
        Return the active Redis client, connecting if necessary.

        Raises:
            RedisError: if the connection cannot be established.
        """

        if self._client is None:
            await self.connect()

        assert self._client is not None  # For type-checkers
        return self._client

    async def close(self) -> None:
        """Close Redis connection."""

        if self._client is None:
            return

        async with self._lock:
            if self._client is None:
                return

            logger.info("Closing Redis connection")
            await self._client.close()
            self._client = None

    def make_key(self, *parts: str) -> str:
        """Return a namespaced Redis key."""

        return ":".join([self._namespace, *parts])


redis_manager = RedisManager(settings.REDIS_URL)

