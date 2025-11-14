from __future__ import annotations

import uuid
from datetime import datetime, timezone

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.exercise import ExerciseResultType
from app.models.language_profile import LanguageProfile
from app.models.topic import Topic, TopicType
from app.models.user import User
from app.repositories.topic import TopicRepository


def _build_user() -> User:
    return User(
        id=uuid.uuid4(),
        telegram_id=123456,
        first_name="Test",
        last_name=None,
        username="tester",
        is_premium=False,
        is_admin=False,
    )


def _build_profile(user: User, language: str = "es") -> LanguageProfile:
    return LanguageProfile(
        id=uuid.uuid4(),
        user_id=user.id,
        language=language,
        language_name="?????????",
        current_level="A2",
        target_level="B1",
        goals=["travel"],
        interface_language="ru",
        is_active=True,
        created_at=datetime.now(tz=timezone.utc),
        updated_at=datetime.now(tz=timezone.utc),
    )


def _build_topic(profile: LanguageProfile, name: str) -> Topic:
    return Topic(
        id=uuid.uuid4(),
        profile_id=profile.id,
        name=name,
        description="Sample topic",
        type=TopicType.GRAMMAR,
        is_active=True,
    )


@pytest.mark.asyncio
async def test_topic_repository_filters_by_profile(db_session: AsyncSession) -> None:
    user = _build_user()
    profile_primary = _build_profile(user)
    profile_secondary = _build_profile(user, language="de")
    topic_primary = _build_topic(profile_primary, "Pret�rito Perfecto")
    topic_secondary = _build_topic(profile_secondary, "Konjunktiv II")
    db_session.add_all([user, profile_primary, profile_secondary, topic_primary, topic_secondary])
    await db_session.commit()

    repo = TopicRepository(db_session)

    topics = await repo.list_for_user(user.id, profile_id=profile_primary.id)
    assert len(topics) == 1
    assert topics[0].name == "Pret�rito Perfecto"

    # Update stats and ensure accuracy is recalculated
    await repo.update_stats(topic_primary, ExerciseResultType.CORRECT)
    assert topic_primary.correct_count == 1
    assert pytest.approx(float(topic_primary.accuracy), rel=1e-3) == 1.0

    # Deactivate other topics
    await repo.deactivate_profile_topics(profile_primary.id)
    assert topic_primary.is_active is False
