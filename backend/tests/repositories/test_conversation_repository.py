from __future__ import annotations

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.conversation import MessageRole
from app.models.language_profile import LanguageProfile
from app.repositories.conversation import ConversationRepository
from app.repositories.user import UserRepository


@pytest.mark.asyncio
async def test_add_and_fetch_conversation_messages(db_session: AsyncSession) -> None:
    user_repo = UserRepository(db_session)
    conversation_repo = ConversationRepository(db_session)

    user = await user_repo.create(telegram_id=999, first_name="Test")
    profile = LanguageProfile(
        user_id=user.id,
        language="en",
        language_name="English",
        current_level="A1",
        target_level="A2",
    )
    db_session.add(profile)
    await db_session.flush()

    await conversation_repo.add_message(
        user_id=user.id,
        profile_id=profile.id,
        role=MessageRole.USER,
        content="Hello",
        tokens=5,
    )
    await conversation_repo.add_message(
        user_id=user.id,
        profile_id=profile.id,
        role=MessageRole.ASSISTANT,
        content="Hi there!",
        tokens=7,
    )

    messages = await conversation_repo.get_recent_for_profile(
        user_id=user.id,
        profile_id=profile.id,
        limit=5,
    )

    assert len(messages) == 2
    assert messages[0].content == "Hi there!"
    assert messages[1].content == "Hello"


@pytest.mark.asyncio
async def test_delete_conversation_history(db_session: AsyncSession) -> None:
    user_repo = UserRepository(db_session)
    conversation_repo = ConversationRepository(db_session)

    user = await user_repo.create(telegram_id=555, first_name="ToDelete")
    profile = LanguageProfile(
        user_id=user.id,
        language="es",
        language_name="Spanish",
        current_level="A1",
        target_level="A2",
    )
    db_session.add(profile)
    await db_session.flush()

    await conversation_repo.add_message(
        user_id=user.id,
        profile_id=profile.id,
        role=MessageRole.USER,
        content="Hola",
    )

    deleted = await conversation_repo.delete_for_user(user.id)
    assert deleted == 1
