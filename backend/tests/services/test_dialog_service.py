"""Tests for Dialog service."""

from __future__ import annotations

import uuid
from datetime import datetime, timezone
from unittest.mock import AsyncMock, MagicMock

import pytest

from app.models.conversation import MessageRole
from app.models.language_profile import LanguageProfile
from app.models.user import User
from app.services.dialog import DialogService


@pytest.mark.asyncio
async def test_process_message_saves_to_database() -> None:
    """Test that process_message saves both user and assistant messages."""
    # Mock dependencies
    mock_llm = AsyncMock()
    mock_llm.chat = AsyncMock(return_value="LLM response")

    mock_repo = AsyncMock()
    mock_repo.session = AsyncMock()
    mock_repo.session.commit = AsyncMock()
    mock_repo.session.refresh = AsyncMock()

    # Mock conversation history (empty)
    mock_repo.get_recent_for_profile = AsyncMock(return_value=[])

    # Mock add_message to return message objects
    user_message = MagicMock()
    user_message.role = MessageRole.USER
    user_message.content = "Hello"

    assistant_message = MagicMock()
    assistant_message.role = MessageRole.ASSISTANT
    assistant_message.content = "LLM response"

    mock_repo.add_message = AsyncMock(side_effect=[user_message, assistant_message])

    # Create service
    service = DialogService(mock_llm, mock_repo)

    # Create test user
    user = User(
        id=uuid.uuid4(),
        telegram_id=123456,
        first_name="Test",
        language_code="ru",
        created_at=datetime.now(tz=timezone.utc),
        updated_at=datetime.now(tz=timezone.utc),
    )

    profile_id = uuid.uuid4()

    # Process message
    response = await service.process_message(
        user=user,
        profile_id=profile_id,
        message="Hello",
    )

    # Assert
    assert response == "LLM response"

    # Verify user message was saved
    assert mock_repo.add_message.call_count == 2

    # Check first call (user message)
    first_call = mock_repo.add_message.call_args_list[0]
    assert first_call.kwargs["user_id"] == user.id
    assert first_call.kwargs["profile_id"] == profile_id
    assert first_call.kwargs["role"] == MessageRole.USER
    assert first_call.kwargs["content"] == "Hello"

    # Check second call (assistant message)
    second_call = mock_repo.add_message.call_args_list[1]
    assert second_call.kwargs["user_id"] == user.id
    assert second_call.kwargs["profile_id"] == profile_id
    assert second_call.kwargs["role"] == MessageRole.ASSISTANT
    assert second_call.kwargs["content"] == "LLM response"

    # Verify LLM was called
    mock_llm.chat.assert_awaited_once()


@pytest.mark.asyncio
async def test_process_message_includes_history() -> None:
    """Test that process_message includes conversation history in LLM call."""
    mock_llm = AsyncMock()
    mock_llm.chat = AsyncMock(return_value="Response with context")

    mock_repo = AsyncMock()
    mock_repo.session = AsyncMock()
    mock_repo.session.commit = AsyncMock()
    mock_repo.session.refresh = AsyncMock()

    # Mock conversation history with previous messages
    prev_user_msg = MagicMock()
    prev_user_msg.role = MessageRole.USER
    prev_user_msg.content = "Previous question"

    prev_asst_msg = MagicMock()
    prev_asst_msg.role = MessageRole.ASSISTANT
    prev_asst_msg.content = "Previous answer"

    current_user_msg = MagicMock()
    current_user_msg.role = MessageRole.USER
    current_user_msg.content = "Current question"

    # History is in DESC order, so newest first
    mock_repo.get_recent_for_profile = AsyncMock(
        return_value=[current_user_msg, prev_asst_msg, prev_user_msg]
    )

    mock_repo.add_message = AsyncMock(return_value=MagicMock())

    service = DialogService(mock_llm, mock_repo)

    user = User(
        id=uuid.uuid4(),
        telegram_id=123456,
        first_name="Test",
        language_code="en",
        created_at=datetime.now(tz=timezone.utc),
        updated_at=datetime.now(tz=timezone.utc),
    )

    profile_id = uuid.uuid4()

    await service.process_message(
        user=user,
        profile_id=profile_id,
        message="Current question",
    )

    # Verify LLM was called with history
    mock_llm.chat.assert_awaited_once()
    call_args = mock_llm.chat.call_args

    messages = call_args.kwargs["messages"]

    # Should have: system prompt + 2 history messages + current message
    assert len(messages) == 4
    assert messages[0]["role"] == "system"
    assert messages[1]["role"] == "user"
    assert messages[1]["content"] == "Previous question"
    assert messages[2]["role"] == "assistant"
    assert messages[2]["content"] == "Previous answer"
    assert messages[3]["role"] == "user"
    assert messages[3]["content"] == "Current question"


@pytest.mark.asyncio
async def test_get_or_create_default_profile_creates_new() -> None:
    """Test that get_or_create_default_profile creates a new profile if none exists."""
    mock_llm = AsyncMock()
    mock_repo = AsyncMock()

    service = DialogService(mock_llm, mock_repo)

    # Mock session
    mock_session = AsyncMock()
    mock_result = MagicMock()
    mock_result.scalar_one_or_none.return_value = None
    mock_session.execute = AsyncMock(return_value=mock_result)
    mock_session.add = MagicMock()
    mock_session.flush = AsyncMock()
    mock_session.refresh = AsyncMock()

    user = User(
        id=uuid.uuid4(),
        telegram_id=123456,
        first_name="Test",
        language_code="ru",
        created_at=datetime.now(tz=timezone.utc),
        updated_at=datetime.now(tz=timezone.utc),
    )

    profile = await service.get_or_create_default_profile(user, mock_session)

    # Verify profile was created
    assert isinstance(profile, LanguageProfile)
    assert profile.user_id == user.id
    assert profile.language == "en"
    assert profile.current_level == "A1"
    assert profile.is_active is True

    mock_session.add.assert_called_once()
    mock_session.flush.assert_awaited_once()


@pytest.mark.asyncio
async def test_get_or_create_default_profile_returns_existing() -> None:
    """Test that get_or_create_default_profile returns existing profile."""
    mock_llm = AsyncMock()
    mock_repo = AsyncMock()

    service = DialogService(mock_llm, mock_repo)

    # Mock existing profile
    existing_profile = LanguageProfile(
        id=uuid.uuid4(),
        user_id=uuid.uuid4(),
        language="es",
        language_name="Spanish",
        current_level="B1",
        target_level="C1",
        goals=["travel"],
        is_active=True,
    )

    # Mock session that returns existing profile
    mock_session = AsyncMock()
    mock_result = MagicMock()
    mock_result.scalar_one_or_none.return_value = existing_profile
    mock_session.execute = AsyncMock(return_value=mock_result)
    mock_session.add = MagicMock()

    user = User(
        id=existing_profile.user_id,
        telegram_id=123456,
        first_name="Test",
        language_code="ru",
        created_at=datetime.now(tz=timezone.utc),
        updated_at=datetime.now(tz=timezone.utc),
    )

    profile = await service.get_or_create_default_profile(user, mock_session)

    # Verify existing profile was returned
    assert profile is existing_profile
    assert profile.language == "es"

    # Verify no new profile was created
    mock_session.add.assert_not_called()
