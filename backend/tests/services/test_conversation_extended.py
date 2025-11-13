"""Extended tests for conversation service."""

from __future__ import annotations

from unittest.mock import AsyncMock
from uuid import uuid4

import pytest

from app.models.conversation import MessageRole
from app.services.conversation import ConversationService


@pytest.mark.asyncio
async def test_add_message_with_all_parameters() -> None:
    """Test add_message with all parameters."""
    repository = AsyncMock()
    service = ConversationService(repository)

    user_id = uuid4()
    profile_id = uuid4()

    expected_message = object()
    repository.add_message.return_value = expected_message

    result = await service.add_message(
        user_id=user_id,
        profile_id=profile_id,
        role=MessageRole.ASSISTANT,
        content="Response",
        tokens=100,
    )

    repository.add_message.assert_awaited_once()
    assert result is expected_message


@pytest.mark.asyncio
async def test_get_recent_with_default_limit() -> None:
    """Test get_recent with default limit."""
    repository = AsyncMock()
    repository.get_recent_for_profile.return_value = []

    service = ConversationService(repository)

    user_id = uuid4()
    profile_id = uuid4()

    await service.get_recent(user_id=user_id, profile_id=profile_id)

    repository.get_recent_for_profile.assert_awaited_once()
    call_kwargs = repository.get_recent_for_profile.call_args.kwargs
    assert "limit" in call_kwargs


@pytest.mark.asyncio
async def test_add_message_user_role() -> None:
    """Test adding user message."""
    repository = AsyncMock()
    service = ConversationService(repository)

    await service.add_message(
        user_id=uuid4(),
        profile_id=uuid4(),
        role=MessageRole.USER,
        content="Hello",
        tokens=5,
    )

    call_args = repository.add_message.call_args
    assert call_args.kwargs["role"] == MessageRole.USER


@pytest.mark.asyncio
async def test_get_recent_returns_list() -> None:
    """Test that get_recent returns result from repository."""
    repository = AsyncMock()
    expected_list = [object(), object()]
    repository.get_recent_for_profile.return_value = expected_list

    service = ConversationService(repository)

    messages = await service.get_recent(
        user_id=uuid4(),
        profile_id=uuid4(),
        limit=10,
    )

    assert messages is expected_list
