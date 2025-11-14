from __future__ import annotations

import uuid
from datetime import datetime, timezone

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.language_profile import LanguageProfile
from app.models.topic import TopicType
from app.models.user import User
from app.repositories.language_profile import LanguageProfileRepository
from app.repositories.topic import TopicRepository
from app.schemas.topic import TopicCreateRequest
from app.services.topic import TopicService


def _build_user() -> User:
    return User(
        id=uuid.uuid4(),
        telegram_id=987654,
        first_name="Service",
        last_name=None,
        username="svc",
        is_premium=False,
        is_admin=False,
    )


def _build_profile(user: User) -> LanguageProfile:
    now = datetime.now(tz=timezone.utc)
    return LanguageProfile(
        id=uuid.uuid4(),
        user_id=user.id,
        language="es",
        language_name="?????????",
        current_level="A2",
        target_level="B1",
        goals=["travel"],
        interface_language="ru",
        is_active=True,
        created_at=now,
        updated_at=now,
    )


@pytest.mark.asyncio
async def test_first_topic_becomes_active(db_session: AsyncSession) -> None:
    user = _build_user()
    profile = _build_profile(user)
    db_session.add_all([user, profile])
    await db_session.commit()

    topic_repo = TopicRepository(db_session)
    profile_repo = LanguageProfileRepository(db_session)
    service = TopicService(topic_repo, profile_repo, llm_service=None)

    payload = TopicCreateRequest(
        profile_id=profile.id, name="Basics", description=None, type=TopicType.GRAMMAR
    )
    first = await service.create_topic(user, payload)
    assert first.is_active is True
    await service.session.commit()

    second_payload = TopicCreateRequest(
        profile_id=profile.id,
        name="Advanced",
        description=None,
        type=TopicType.GRAMMAR,
    )
    second = await service.create_topic(user, second_payload)
    assert second.is_active is False
