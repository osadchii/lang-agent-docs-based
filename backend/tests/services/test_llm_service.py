"""Tests for LLM service."""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock

import pytest

from app.services.llm import LLMService, get_basic_system_prompt


@pytest.mark.asyncio
async def test_llm_chat_success() -> None:
    """Test successful LLM chat completion."""
    service = LLMService(api_key="test-key", model="gpt-4o-mini")

    # Mock the OpenAI client
    mock_response = MagicMock()
    mock_response.choices = [MagicMock()]
    mock_response.choices[0].message.content = "Test response"
    mock_response.usage = MagicMock()
    mock_response.usage.prompt_tokens = 10
    mock_response.usage.completion_tokens = 20

    service.client.chat.completions.create = AsyncMock(return_value=mock_response)

    # Call the service
    result = await service.chat(
        messages=[{"role": "user", "content": "Hello"}],
        temperature=0.7,
    )

    assert result == "Test response"
    service.client.chat.completions.create.assert_awaited_once()


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

    result = await service.chat(messages=[{"role": "user", "content": "Hello"}])

    assert result == ""


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
