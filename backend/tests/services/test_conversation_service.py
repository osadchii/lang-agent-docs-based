from __future__ import annotations

from unittest.mock import AsyncMock
from uuid import uuid4

import pytest

from app.models.conversation import MessageRole
from app.services.conversation import ConversationService


@pytest.mark.asyncio
async def test_add_message_delegates_to_repository() -> None:
    repository = AsyncMock()
    service = ConversationService(repository)

    user_id = uuid4()
    profile_id = uuid4()

    expected_message = object()
    repository.add_message.return_value = expected_message

    result = await service.add_message(
        user_id=user_id,
        profile_id=profile_id,
        role=MessageRole.USER,
        content="hello",
        tokens=42,
    )

    repository.add_message.assert_awaited_once_with(
        user_id=user_id,
        profile_id=profile_id,
        role=MessageRole.USER,
        content="hello",
        tokens=42,
    )
    assert result is expected_message


@pytest.mark.asyncio
async def test_get_recent_proxies_arguments() -> None:
    repository = AsyncMock()
    service = ConversationService(repository)

    user_id = uuid4()
    profile_id = uuid4()

    await service.get_recent(user_id=user_id, profile_id=profile_id, limit=5)

    repository.get_recent_for_profile.assert_awaited_once_with(
        user_id=user_id,
        profile_id=profile_id,
        limit=5,
    )
