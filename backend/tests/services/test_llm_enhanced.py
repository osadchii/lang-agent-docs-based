"""Tests for Enhanced LLM service with structured outputs."""

from __future__ import annotations

from unittest.mock import AsyncMock

import pytest

from app.core.cache import CacheClient
from app.schemas.llm_responses import CardContent, IntentDetection
from app.services.llm import TokenUsage
from app.services.llm_enhanced import EnhancedLLMService


@pytest.fixture
def mock_cache() -> AsyncMock:
    """Create mock cache client."""
    cache = AsyncMock(spec=CacheClient)
    cache.get = AsyncMock(return_value=None)
    cache.set = AsyncMock(return_value=True)
    return cache


@pytest.fixture
def llm_service(mock_cache: AsyncMock) -> EnhancedLLMService:
    """Create enhanced LLM service with mock cache."""
    service = EnhancedLLMService(api_key="test-key", cache=mock_cache, model="gpt-4o-mini")
    # Mock the base chat method to avoid real API calls
    service.chat = AsyncMock()
    return service


@pytest.mark.asyncio
async def test_chat_structured_with_cache_hit(
    llm_service: EnhancedLLMService, mock_cache: AsyncMock
) -> None:
    """Test chat_structured returns cached result when available."""
    # Setup cache hit with valid IntentDetection JSON
    cached_data = '{"intent": "translate", "confidence": 0.95, "entities": {}}'
    mock_cache.get.return_value = cached_data

    messages = [{"role": "user", "content": "Translate this"}]
    result, usage = await llm_service.chat_structured(
        messages=messages,
        response_model=IntentDetection,
        cache_key="test_key",
        cache_ttl=3600,
    )

    # Verify cache was checked
    mock_cache.get.assert_awaited_once_with("test_key")

    # Verify LLM was not called
    llm_service.chat.assert_not_awaited()

    # Verify result
    assert isinstance(result, IntentDetection)
    assert result.intent == "translate"
    assert usage.total_tokens == 0


@pytest.mark.asyncio
async def test_chat_structured_with_cache_miss(
    llm_service: EnhancedLLMService, mock_cache: AsyncMock
) -> None:
    """Test chat_structured calls LLM on cache miss."""
    # Setup cache miss
    mock_cache.get.return_value = None

    # Setup LLM response
    llm_response = '{"intent": "practice", "confidence": 0.9, "entities": {}}'
    llm_service.chat.return_value = (llm_response, TokenUsage(100, 50, 150))

    messages = [{"role": "user", "content": "I want to practice"}]
    result, usage = await llm_service.chat_structured(
        messages=messages,
        response_model=IntentDetection,
        cache_key="test_key",
        cache_ttl=3600,
    )

    # Verify cache was checked
    mock_cache.get.assert_awaited_once_with("test_key")

    # Verify LLM was called with JSON mode
    llm_service.chat.assert_awaited_once()
    call_kwargs = llm_service.chat.call_args.kwargs
    assert call_kwargs["response_format"] == {"type": "json_object"}

    # Verify result was cached
    mock_cache.set.assert_awaited_once()

    # Verify result
    assert isinstance(result, IntentDetection)
    assert result.intent == "practice"
    assert usage.total_tokens == 150


@pytest.mark.asyncio
async def test_generate_card(llm_service: EnhancedLLMService, mock_cache: AsyncMock) -> None:
    """Test generate_card method."""
    # Setup LLM response
    card_json = """{
        "word": "casa",
        "lemma": "casa",
        "translation": "дом",
        "example": "Mi casa es tu casa",
        "example_translation": "Мой дом - твой дом",
        "notes": null
    }"""
    llm_service.chat.return_value = (card_json, TokenUsage(100, 50, 150))

    result, usage = await llm_service.generate_card(
        word="casa",
        language="es",
        language_name="Spanish",
        level="A1",
        goals=["conversation", "travel"],
    )

    # Verify result
    assert isinstance(result, CardContent)
    assert result.word == "casa"
    assert result.translation == "дом"
    assert usage.total_tokens == 150


@pytest.mark.asyncio
async def test_get_lemma(llm_service: EnhancedLLMService, mock_cache: AsyncMock) -> None:
    """Test get_lemma method."""
    # Setup cache miss
    mock_cache.get.return_value = None

    # Setup LLM response (returns plain text, not JSON)
    llm_service.chat.return_value = ("casa", TokenUsage(50, 10, 60))

    result, usage = await llm_service.get_lemma(word="casas", language="es")

    # Verify result
    assert result == "casa"
    assert usage.total_tokens == 60

    # Verify permanent caching was used
    mock_cache.set.assert_awaited_once()
    call_args = mock_cache.set.call_args
    assert call_args.kwargs["ttl"] is None


@pytest.mark.asyncio
async def test_get_lemma_from_cache(llm_service: EnhancedLLMService, mock_cache: AsyncMock) -> None:
    """Test get_lemma uses cache."""
    # Setup cache hit
    mock_cache.get.return_value = "hacer"

    result, usage = await llm_service.get_lemma(word="hice", language="es")

    # Verify result from cache
    assert result == "hacer"
    assert usage.total_tokens == 0

    # Verify LLM was not called
    llm_service.chat.assert_not_awaited()


@pytest.mark.asyncio
async def test_detect_intent(llm_service: EnhancedLLMService, mock_cache: AsyncMock) -> None:
    """Test detect_intent method."""
    # Setup LLM response
    intent_json = '{"intent": "translate", "confidence": 0.9, "entities": {}}'
    llm_service.chat.return_value = (intent_json, TokenUsage(80, 30, 110))

    result, usage = await llm_service.detect_intent(user_message="Translate 'hello' to Spanish")

    # Verify result
    assert isinstance(result, IntentDetection)
    assert result.intent == "translate"
    assert result.confidence == 0.9
    assert usage.total_tokens == 110


@pytest.mark.asyncio
async def test_cache_key_generation(llm_service: EnhancedLLMService, mock_cache: AsyncMock) -> None:
    """Test that cache keys are properly generated."""
    # Setup LLM response
    card_json = """{
        "word": "perro",
        "lemma": "perro",
        "translation": "собака",
        "example": "El perro es grande",
        "example_translation": "Собака большая",
        "notes": null
    }"""
    llm_service.chat.return_value = (card_json, TokenUsage(100, 50, 150))

    # Call method that should use caching
    await llm_service.generate_card(
        word="perro",
        language="es",
        language_name="Spanish",
        level="A1",
        goals=["conversation"],
    )

    # Verify cache was set with proper key
    mock_cache.set.assert_awaited()
    call_args = mock_cache.set.call_args
    cache_key = call_args[0][0]
    assert cache_key.startswith("card:")


@pytest.mark.asyncio
async def test_chat_structured_without_cache(
    llm_service: EnhancedLLMService, mock_cache: AsyncMock
) -> None:
    """Test chat_structured works without caching."""
    # Setup LLM response
    llm_response = '{"intent": "practice", "confidence": 0.85, "entities": {}}'
    llm_service.chat.return_value = (llm_response, TokenUsage(100, 50, 150))

    messages = [{"role": "user", "content": "Let's practice"}]
    result, usage = await llm_service.chat_structured(
        messages=messages, response_model=IntentDetection
    )

    # Verify cache was not checked
    mock_cache.get.assert_not_awaited()

    # Verify LLM was called
    llm_service.chat.assert_awaited_once()

    # Verify result was not cached
    mock_cache.set.assert_not_awaited()

    # Verify result
    assert isinstance(result, IntentDetection)
    assert result.intent == "practice"


@pytest.mark.asyncio
async def test_generate_card_uses_30day_cache(
    llm_service: EnhancedLLMService, mock_cache: AsyncMock
) -> None:
    """Test that generate_card uses 30-day caching."""
    # Setup cache miss
    mock_cache.get.return_value = None

    # Setup LLM response
    card_json = """{
        "word": "gato",
        "lemma": "gato",
        "translation": "кот",
        "example": "El gato duerme",
        "example_translation": "Кот спит",
        "notes": null
    }"""
    llm_service.chat.return_value = (card_json, TokenUsage(100, 50, 150))

    await llm_service.generate_card(
        word="gato",
        language="es",
        language_name="Spanish",
        level="A1",
        goals=["reading"],
    )

    # Verify cache was set with 30-day TTL
    mock_cache.set.assert_awaited_once()
    call_args = mock_cache.set.call_args
    assert call_args.kwargs["ttl"] == 2_592_000  # 30 days in seconds


@pytest.mark.asyncio
async def test_track_token_usage(llm_service: EnhancedLLMService, mock_cache: AsyncMock) -> None:
    """Test track_token_usage method."""
    from uuid import uuid4

    user_id = str(uuid4())
    profile_id = str(uuid4())
    usage = TokenUsage(prompt_tokens=100, completion_tokens=50, total_tokens=150)

    # Mock the session
    mock_session = AsyncMock()
    mock_session.add = AsyncMock()
    mock_session.commit = AsyncMock()

    await llm_service.track_token_usage(
        db_session=mock_session,
        user_id=user_id,
        profile_id=profile_id,
        usage=usage,
        operation="chat",
    )

    # Verify token usage was saved
    mock_session.add.assert_called_once()
    mock_session.commit.assert_awaited_once()


@pytest.mark.asyncio
async def test_chat_structured_validates_response_format(
    llm_service: EnhancedLLMService, mock_cache: AsyncMock
) -> None:
    """Test that chat_structured passes JSON mode to chat."""
    intent_json = '{"intent": "translate", "confidence": 0.95, "entities": {}}'
    llm_service.chat.return_value = (intent_json, TokenUsage(100, 50, 150))

    messages = [{"role": "user", "content": "Test"}]
    await llm_service.chat_structured(messages=messages, response_model=IntentDetection)

    # Verify JSON mode was requested
    llm_service.chat.assert_awaited_once()
    call_kwargs = llm_service.chat.call_args.kwargs
    assert "response_format" in call_kwargs
    assert call_kwargs["response_format"] == {"type": "json_object"}


@pytest.mark.asyncio
async def test_chat_structured_with_temperature(
    llm_service: EnhancedLLMService, mock_cache: AsyncMock
) -> None:
    """Test that temperature parameter is passed through."""
    intent_json = '{"intent": "practice", "confidence": 0.9, "entities": {}}'
    llm_service.chat.return_value = (intent_json, TokenUsage(80, 40, 120))

    messages = [{"role": "user", "content": "Practice"}]
    await llm_service.chat_structured(
        messages=messages, response_model=IntentDetection, temperature=0.5
    )

    call_kwargs = llm_service.chat.call_args.kwargs
    assert call_kwargs["temperature"] == 0.5


@pytest.mark.asyncio
async def test_chat_structured_with_max_tokens(
    llm_service: EnhancedLLMService, mock_cache: AsyncMock
) -> None:
    """Test that max_tokens parameter is passed through."""
    intent_json = '{"intent": "translate", "confidence": 0.85, "entities": {}}'
    llm_service.chat.return_value = (intent_json, TokenUsage(90, 45, 135))

    messages = [{"role": "user", "content": "Test"}]
    await llm_service.chat_structured(
        messages=messages, response_model=IntentDetection, max_tokens=200
    )

    call_kwargs = llm_service.chat.call_args.kwargs
    assert call_kwargs["max_tokens"] == 200
