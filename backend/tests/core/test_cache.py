"""Tests for Redis cache module."""

from __future__ import annotations

from unittest.mock import AsyncMock

import pytest

from app.core.cache import (
    TTL_1_HOUR,
    TTL_30_DAYS,
    TTL_PERMANENT,
    CacheClient,
    card_cache_key,
    generic_llm_cache_key,
    lemma_cache_key,
    topics_cache_key,
    translation_cache_key,
)


@pytest.fixture
def mock_redis() -> AsyncMock:
    """Create mock Redis client."""
    redis = AsyncMock()
    redis.get = AsyncMock(return_value=None)
    redis.set = AsyncMock(return_value=True)
    redis.setex = AsyncMock(return_value=True)
    redis.delete = AsyncMock(return_value=1)
    redis.exists = AsyncMock(return_value=False)
    redis.close = AsyncMock()
    redis.expire = AsyncMock(return_value=True)
    redis.ttl = AsyncMock(return_value=60)
    redis.incr = AsyncMock(return_value=1)
    redis.sadd = AsyncMock(return_value=1)
    redis.smembers = AsyncMock(return_value=set())
    redis.srem = AsyncMock(return_value=0)
    return redis


@pytest.fixture
def cache_client(mock_redis: AsyncMock) -> CacheClient:
    """Create cache client with mock Redis."""
    client = CacheClient(redis_url="redis://localhost:6379/0")
    client._redis = mock_redis
    return client


class TestCacheClient:
    """Tests for CacheClient."""

    @pytest.mark.asyncio
    @pytest.mark.asyncio
    async def test_get_miss(self, cache_client: CacheClient, mock_redis: AsyncMock) -> None:
        """Test cache miss."""
        mock_redis.get.return_value = None

        value = await cache_client.get("test_key")

        assert value is None
        mock_redis.get.assert_called_once_with("test_key")

    @pytest.mark.asyncio
    async def test_get_hit(self, cache_client: CacheClient, mock_redis: AsyncMock) -> None:
        """Test cache hit."""
        mock_redis.get.return_value = '{"data": "test"}'

        value = await cache_client.get("test_key")

        assert value == '{"data": "test"}'
        mock_redis.get.assert_called_once_with("test_key")

    @pytest.mark.asyncio
    async def test_set_with_ttl(self, cache_client: CacheClient, mock_redis: AsyncMock) -> None:
        """Test setting value with TTL."""
        await cache_client.set("test_key", "test_value", ttl=3600)

        mock_redis.setex.assert_called_once_with("test_key", 3600, "test_value")

    @pytest.mark.asyncio
    async def test_set_without_ttl(self, cache_client: CacheClient, mock_redis: AsyncMock) -> None:
        """Test setting value without TTL (permanent)."""
        await cache_client.set("test_key", "test_value", ttl=None)

        mock_redis.set.assert_called_once_with("test_key", "test_value")

    @pytest.mark.asyncio
    async def test_delete(self, cache_client: CacheClient, mock_redis: AsyncMock) -> None:
        """Test deleting key."""
        mock_redis.delete.return_value = 1

        result = await cache_client.delete("test_key")

        assert result is True
        mock_redis.delete.assert_called_once_with("test_key")

    @pytest.mark.asyncio
    async def test_delete_nonexistent(
        self, cache_client: CacheClient, mock_redis: AsyncMock
    ) -> None:
        """Test deleting non-existent key."""
        mock_redis.delete.return_value = 0

        result = await cache_client.delete("nonexistent_key")

        assert result is False

    @pytest.mark.asyncio
    async def test_exists_true(self, cache_client: CacheClient, mock_redis: AsyncMock) -> None:
        """Test checking if key exists (true)."""
        mock_redis.exists.return_value = 1

        result = await cache_client.exists("test_key")

        assert result is True
        mock_redis.exists.assert_called_once_with("test_key")

    @pytest.mark.asyncio
    async def test_exists_false(self, cache_client: CacheClient, mock_redis: AsyncMock) -> None:
        """Test checking if key exists (false)."""
        mock_redis.exists.return_value = 0

        result = await cache_client.exists("nonexistent_key")

        assert result is False

    @pytest.mark.asyncio
    async def test_get_without_connection(self) -> None:
        """Test that operations require connection.

        Since get() handles errors gracefully and returns None,
        we test that accessing redis property raises RuntimeError.
        """
        client = CacheClient(redis_url="redis://localhost:6379/0")
        # Don't connect

        with pytest.raises(RuntimeError, match="not connected"):
            _ = client.redis

    @pytest.mark.asyncio
    async def test_disconnect(self, cache_client: CacheClient, mock_redis: AsyncMock) -> None:
        """Test disconnecting from Redis."""
        await cache_client.disconnect()

        mock_redis.close.assert_called_once()
        assert cache_client._redis is None


class TestCacheKeyBuilders:
    """Tests for cache key builder functions."""

    def test_card_cache_key(self) -> None:
        """Test card cache key builder."""
        key = card_cache_key("es", "casa")

        assert key == "card:es:casa"

    def test_card_cache_key_lowercase(self) -> None:
        """Test card cache key normalizes to lowercase."""
        key = card_cache_key("es", "Casa")

        assert key == "card:es:casa"

    def test_lemma_cache_key(self) -> None:
        """Test lemma cache key builder."""
        key = lemma_cache_key("de", "Häuser")

        assert key == "lemma:de:häuser"

    def test_translation_cache_key(self) -> None:
        """Test translation cache key builder."""
        key = translation_cache_key("en", "ru", "house")

        assert key == "translation:en:ru:house"

    def test_topics_cache_key(self) -> None:
        """Test topics cache key builder."""
        profile_id = "123e4567-e89b-12d3-a456-426614174000"
        key = topics_cache_key(profile_id)

        assert key == f"topics:{profile_id}"

    def test_generic_llm_cache_key(self) -> None:
        """Test generic LLM cache key builder."""
        key1 = generic_llm_cache_key("generate_exercise", topic="grammar", level="B1")
        key2 = generic_llm_cache_key("generate_exercise", level="B1", topic="grammar")

        # Keys should be identical regardless of parameter order
        assert key1 == key2
        assert key1.startswith("llm:generate_exercise:")

    def test_generic_llm_cache_key_different_params(self) -> None:
        """Test that different params produce different keys."""
        key1 = generic_llm_cache_key("generate_exercise", topic="grammar")
        key2 = generic_llm_cache_key("generate_exercise", topic="vocabulary")

        assert key1 != key2


class TestCacheTTLConstants:
    """Tests for TTL constants."""

    def test_ttl_30_days(self) -> None:
        """Test 30-day TTL constant."""
        assert TTL_30_DAYS == 30 * 24 * 3600
        assert TTL_30_DAYS == 2_592_000

    def test_ttl_1_hour(self) -> None:
        """Test 1-hour TTL constant."""
        assert TTL_1_HOUR == 3600

    def test_ttl_permanent(self) -> None:
        """Test permanent TTL constant (None)."""
        assert TTL_PERMANENT is None


class TestCacheErrorHandling:
    """Tests for cache error handling."""

    @pytest.mark.asyncio
    async def test_get_with_redis_error(
        self, cache_client: CacheClient, mock_redis: AsyncMock
    ) -> None:
        """Test that get returns None on Redis error."""
        mock_redis.get.side_effect = Exception("Redis connection error")

        value = await cache_client.get("test_key")

        assert value is None

    @pytest.mark.asyncio
    async def test_set_with_redis_error(
        self, cache_client: CacheClient, mock_redis: AsyncMock
    ) -> None:
        """Test that set returns False on Redis error."""
        mock_redis.setex.side_effect = Exception("Redis connection error")

        result = await cache_client.set("test_key", "value", ttl=3600)

        assert result is False

    @pytest.mark.asyncio
    async def test_delete_with_redis_error(
        self, cache_client: CacheClient, mock_redis: AsyncMock
    ) -> None:
        """Test that delete returns False on Redis error."""
        mock_redis.delete.side_effect = Exception("Redis connection error")

        result = await cache_client.delete("test_key")

        assert result is False

    @pytest.mark.asyncio
    async def test_exists_with_redis_error(
        self, cache_client: CacheClient, mock_redis: AsyncMock
    ) -> None:
        """Test that exists returns False on Redis error."""
        mock_redis.exists.side_effect = Exception("Redis connection error")

        result = await cache_client.exists("test_key")

        assert result is False


class TestCacheConnection:
    """Tests for cache connection management."""

    @pytest.mark.asyncio
    async def test_connect(self) -> None:
        """Test connecting to Redis."""
        client = CacheClient(redis_url="redis://localhost:6379/0")

        # Mock redis connection
        with pytest.raises(RuntimeError, match="not connected"):
            _ = client.redis

    @pytest.mark.asyncio
    async def test_disconnect_when_not_connected(self) -> None:
        """Test disconnecting when not connected."""
        client = CacheClient(redis_url="redis://localhost:6379/0")

        # Should not raise error
        await client.disconnect()

        assert client._redis is None

    @pytest.mark.asyncio
    async def test_connect_creates_redis_client(self) -> None:
        """Test that connect creates redis client."""
        client = CacheClient(redis_url="redis://localhost:6379/0")

        # Should not be connected initially
        assert client._redis is None

        await client.connect()

        # Should be connected after connect()
        assert client._redis is not None


class TestCacheIntegration:
    """Integration tests for cache operations."""

    @pytest.mark.asyncio
    async def test_set_and_get_roundtrip(
        self, cache_client: CacheClient, mock_redis: AsyncMock
    ) -> None:
        """Test setting and getting value in sequence."""
        # Set value
        mock_redis.setex.return_value = True
        await cache_client.set("key1", "value1", ttl=60)

        # Get value
        mock_redis.get.return_value = "value1"
        result = await cache_client.get("key1")

        assert result == "value1"

    @pytest.mark.asyncio
    async def test_set_then_delete(self, cache_client: CacheClient, mock_redis: AsyncMock) -> None:
        """Test setting then deleting a key."""
        # Set
        mock_redis.set.return_value = True
        await cache_client.set("temp_key", "temp_value", ttl=None)

        # Delete
        mock_redis.delete.return_value = 1
        result = await cache_client.delete("temp_key")

        assert result is True

    @pytest.mark.asyncio
    async def test_exists_after_set(self, cache_client: CacheClient, mock_redis: AsyncMock) -> None:
        """Test checking existence after setting."""
        # Set
        mock_redis.setex.return_value = True
        await cache_client.set("exists_key", "value", ttl=120)

        # Check exists
        mock_redis.exists.return_value = 1
        exists = await cache_client.exists("exists_key")

        assert exists is True


class TestCacheKeyNormalization:
    """Test cache key normalization."""

    def test_card_key_with_uppercase(self) -> None:
        """Test card key normalizes uppercase."""
        key1 = card_cache_key("es", "CASA")
        key2 = card_cache_key("es", "casa")

        assert key1 == key2
        assert key1 == "card:es:casa"

    def test_lemma_key_with_mixed_case(self) -> None:
        """Test lemma key normalizes mixed case."""
        key1 = lemma_cache_key("de", "HäUser")
        key2 = lemma_cache_key("de", "häuser")

        assert key1 == key2

    def test_translation_key_structure(self) -> None:
        """Test translation key has correct structure."""
        key = translation_cache_key("en", "ru", "hello")

        assert key.startswith("translation:")
        assert "en" in key
        assert "ru" in key
        assert "hello" in key

    def test_generic_llm_key_parameter_order(self) -> None:
        """Test generic LLM key is order-independent."""
        key1 = generic_llm_cache_key("test_op", a="1", b="2", c="3")
        key2 = generic_llm_cache_key("test_op", c="3", a="1", b="2")

        assert key1 == key2

    def test_generic_llm_key_with_different_values(self) -> None:
        """Test generic LLM key changes with different values."""
        key1 = generic_llm_cache_key("op", param="value1")
        key2 = generic_llm_cache_key("op", param="value2")

        assert key1 != key2
