"""Tests for LLM service."""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from openai import APIConnectionError, AuthenticationError, BadRequestError, RateLimitError

from app.services.llm import LLMProvider, LLMService, TokenUsage, get_basic_system_prompt


def test_token_usage_calculation() -> None:
    """Test TokenUsage dataclass and cost calculation."""
    usage = TokenUsage(prompt_tokens=1000, completion_tokens=500, total_tokens=1500)

    assert usage.prompt_tokens == 1000
    assert usage.completion_tokens == 500
    assert usage.total_tokens == 1500

    # GPT-4o-mini pricing: $0.15/1M input, $0.60/1M output
    expected_cost = (1000 / 1_000_000) * 0.15 + (500 / 1_000_000) * 0.60
    assert abs(usage.estimated_cost - expected_cost) < 0.0001


def test_llm_provider_enum() -> None:
    """Test LLMProvider enum values."""
    assert LLMProvider.OPENAI.value == "openai"
    assert LLMProvider.ANTHROPIC.value == "anthropic"


def test_llm_service_init_openai() -> None:
    """Test LLMService initialization with OpenAI provider."""
    service = LLMService(
        api_key="test-key",
        model="gpt-4o-mini",
        temperature=0.8,
        provider=LLMProvider.OPENAI,
    )

    assert service.model == "gpt-4o-mini"
    assert service.default_temperature == 0.8
    assert service.provider == LLMProvider.OPENAI
    assert service.client is not None


def test_llm_service_init_anthropic_not_implemented() -> None:
    """Test LLMService initialization with Anthropic provider raises NotImplementedError."""
    with pytest.raises(NotImplementedError, match="Anthropic provider is not yet implemented"):
        LLMService(
            api_key="test-key",
            provider=LLMProvider.ANTHROPIC,
        )


@pytest.mark.asyncio
async def test_llm_chat_success() -> None:
    """Test successful LLM chat completion."""
    service = LLMService(api_key="test-key", model="gpt-4o-mini", temperature=0.7)

    # Mock the OpenAI client
    mock_response = MagicMock()
    mock_response.choices = [MagicMock()]
    mock_response.choices[0].message.content = "Test response"
    mock_response.usage = MagicMock()
    mock_response.usage.prompt_tokens = 100
    mock_response.usage.completion_tokens = 50
    mock_response.usage.total_tokens = 150

    service.client.chat.completions.create = AsyncMock(return_value=mock_response)

    # Call the service
    response, usage = await service.chat(
        messages=[{"role": "user", "content": "Hello"}],
        temperature=0.7,
    )

    assert response == "Test response"
    assert usage.prompt_tokens == 100
    assert usage.completion_tokens == 50
    assert usage.total_tokens == 150
    service.client.chat.completions.create.assert_awaited_once()


@pytest.mark.asyncio
async def test_llm_chat_with_default_temperature() -> None:
    """Test LLM chat uses default temperature when not specified."""
    service = LLMService(api_key="test-key", model="gpt-4o-mini", temperature=0.9)

    mock_response = MagicMock()
    mock_response.choices = [MagicMock()]
    mock_response.choices[0].message.content = "Response"
    mock_response.usage = MagicMock()
    mock_response.usage.prompt_tokens = 10
    mock_response.usage.completion_tokens = 20
    mock_response.usage.total_tokens = 30

    service.client.chat.completions.create = AsyncMock(return_value=mock_response)

    response, usage = await service.chat(messages=[{"role": "user", "content": "Hi"}])

    # Verify default temperature was used
    call_kwargs = service.client.chat.completions.create.call_args.kwargs
    assert call_kwargs["temperature"] == 0.9


@pytest.mark.asyncio
async def test_llm_chat_with_response_format() -> None:
    """Test LLM chat with JSON response format."""
    service = LLMService(api_key="test-key")

    mock_response = MagicMock()
    mock_response.choices = [MagicMock()]
    mock_response.choices[0].message.content = '{"key": "value"}'
    mock_response.usage = MagicMock()
    mock_response.usage.prompt_tokens = 10
    mock_response.usage.completion_tokens = 5
    mock_response.usage.total_tokens = 15

    service.client.chat.completions.create = AsyncMock(return_value=mock_response)

    response, usage = await service.chat(
        messages=[{"role": "user", "content": "Generate JSON"}],
        response_format={"type": "json_object"},
    )

    assert response == '{"key": "value"}'
    call_kwargs = service.client.chat.completions.create.call_args.kwargs
    assert call_kwargs["response_format"] == {"type": "json_object"}


@pytest.mark.asyncio
async def test_llm_chat_null_content() -> None:
    """Test LLM chat when API returns null content."""
    service = LLMService(api_key="test-key")

    # Mock null content response
    mock_response = MagicMock()
    mock_response.choices = [MagicMock()]
    mock_response.choices[0].message.content = None
    mock_response.usage = None

    service.client.chat.completions.create = AsyncMock(return_value=mock_response)

    response, usage = await service.chat(messages=[{"role": "user", "content": "Hello"}])

    assert response == ""
    assert usage.total_tokens == 0


@pytest.mark.asyncio
async def test_llm_chat_authentication_error() -> None:
    """Test LLM chat raises AuthenticationError for invalid API key."""
    service = LLMService(api_key="invalid-key")

    service.client.chat.completions.create = AsyncMock(
        side_effect=AuthenticationError(
            message="Invalid API key",
            response=MagicMock(status_code=401),
            body=None,
        )
    )

    with pytest.raises(AuthenticationError):
        await service.chat(messages=[{"role": "user", "content": "Hello"}])


@pytest.mark.asyncio
async def test_llm_chat_bad_request_error() -> None:
    """Test LLM chat raises BadRequestError for invalid parameters."""
    service = LLMService(api_key="test-key")

    service.client.chat.completions.create = AsyncMock(
        side_effect=BadRequestError(
            message="Invalid request",
            response=MagicMock(status_code=400),
            body=None,
        )
    )

    with pytest.raises(BadRequestError):
        await service.chat(messages=[{"role": "user", "content": ""}])


@pytest.mark.asyncio
async def test_llm_chat_rate_limit_retries() -> None:
    """Test LLM chat retries on RateLimitError and eventually succeeds."""
    service = LLMService(api_key="test-key")

    # First two calls raise RateLimitError, third succeeds
    mock_response = MagicMock()
    mock_response.choices = [MagicMock()]
    mock_response.choices[0].message.content = "Success after retry"
    mock_response.usage = MagicMock()
    mock_response.usage.prompt_tokens = 10
    mock_response.usage.completion_tokens = 20
    mock_response.usage.total_tokens = 30

    service.client.chat.completions.create = AsyncMock(
        side_effect=[
            RateLimitError(
                message="Rate limit exceeded",
                response=MagicMock(status_code=429),
                body=None,
            ),
            RateLimitError(
                message="Rate limit exceeded",
                response=MagicMock(status_code=429),
                body=None,
            ),
            mock_response,
        ]
    )

    # Should succeed after retries
    with patch("app.services.llm.wait_exponential") as mock_wait:
        # Speed up the test by making wait time instant
        mock_wait.return_value = lambda retry_state: 0

        response, usage = await service.chat(messages=[{"role": "user", "content": "Test"}])

        assert response == "Success after retry"
        assert service.client.chat.completions.create.call_count == 3


@pytest.mark.asyncio
async def test_llm_chat_rate_limit_exhausted() -> None:
    """Test LLM chat fails after exhausting retries on RateLimitError."""
    service = LLMService(api_key="test-key")

    # All calls raise RateLimitError
    service.client.chat.completions.create = AsyncMock(
        side_effect=RateLimitError(
            message="Rate limit exceeded",
            response=MagicMock(status_code=429),
            body=None,
        )
    )

    with patch("app.services.llm.wait_exponential") as mock_wait:
        mock_wait.return_value = lambda retry_state: 0

        with pytest.raises(RateLimitError):
            await service.chat(messages=[{"role": "user", "content": "Test"}])

        # Should attempt 3 times (initial + 2 retries)
        assert service.client.chat.completions.create.call_count == 3


@pytest.mark.asyncio
async def test_llm_chat_connection_error_retries() -> None:
    """Test LLM chat retries on APIConnectionError."""
    service = LLMService(api_key="test-key")

    mock_response = MagicMock()
    mock_response.choices = [MagicMock()]
    mock_response.choices[0].message.content = "Connected"
    mock_response.usage = MagicMock()
    mock_response.usage.prompt_tokens = 5
    mock_response.usage.completion_tokens = 10
    mock_response.usage.total_tokens = 15

    # First call fails, second succeeds
    service.client.chat.completions.create = AsyncMock(
        side_effect=[
            APIConnectionError(message="Connection failed", request=MagicMock()),
            mock_response,
        ]
    )

    with patch("app.services.llm.wait_exponential") as mock_wait:
        mock_wait.return_value = lambda retry_state: 0

        response, usage = await service.chat(messages=[{"role": "user", "content": "Test"}])

        assert response == "Connected"
        assert service.client.chat.completions.create.call_count == 2


def test_get_basic_system_prompt_russian() -> None:
    """Test basic system prompt generation for Russian users."""
    prompt = get_basic_system_prompt(language_code="ru")

    assert "Russian" in prompt
    assert "language teacher" in prompt
    assert "encouraging" in prompt


def test_get_basic_system_prompt_english() -> None:
    """Test basic system prompt generation for English users."""
    prompt = get_basic_system_prompt(language_code="en")

    assert "English" in prompt
    assert "language teacher" in prompt


def test_get_basic_system_prompt_default() -> None:
    """Test basic system prompt defaults to Russian when no language code."""
    prompt = get_basic_system_prompt(language_code=None)

    assert "Russian" in prompt
