from __future__ import annotations

import uuid
from datetime import datetime, timezone

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.exercise import ExerciseResultType, ExerciseType
from app.models.language_profile import LanguageProfile
from app.models.topic import Topic, TopicType
from app.models.user import User
from app.repositories.exercise import ExerciseHistoryRepository


def _build_user() -> User:
    return User(
        id=uuid.uuid4(),
        telegram_id=654321,
        first_name="Learner",
        last_name=None,
        username="student",
        is_premium=False,
        is_admin=False,
    )


def _build_profile(user: User) -> LanguageProfile:
    return LanguageProfile(
        id=uuid.uuid4(),
        user_id=user.id,
        language="es",
        language_name="?????????",
        current_level="A2",
        target_level="B1",
        goals=["communication"],
        interface_language="ru",
        is_active=True,
        created_at=datetime.now(tz=timezone.utc),
        updated_at=datetime.now(tz=timezone.utc),
    )


def _build_topic(profile: LanguageProfile) -> Topic:
    return Topic(
        id=uuid.uuid4(),
        profile_id=profile.id,
        name="Pret�rito Perfecto",
        description="????????? ?????",
        type=TopicType.GRAMMAR,
    )


@pytest.mark.asyncio
async def test_record_and_list_history(db_session: AsyncSession) -> None:
    user = _build_user()
    profile = _build_profile(user)
    topic = _build_topic(profile)
    db_session.add_all([user, profile, topic])
    await db_session.commit()

    repo = ExerciseHistoryRepository(db_session)
    await repo.record_attempt(
        user_id=user.id,
        profile_id=profile.id,
        topic_id=topic.id,
        exercise_type=ExerciseType.FREE_TEXT,
        question="?????????? ?? ?????????:",
        prompt="Yo ____ en Madrid?",
        correct_answer="He vivido",
        user_answer="He vivido",
        result=ExerciseResultType.CORRECT,
        explanation="???????? Pret�rito Perfecto",
        used_hint=False,
        duration_seconds=30,
        metadata={"difficulty": "medium"},
    )

    entries, total = await repo.list_for_user(user.id)
    assert total == 1
    assert entries[0].user_answer == "He vivido"

    recent = await repo.last_results_for_topic(topic.id, limit=1)
    assert len(recent) == 1
    assert recent[0].result == ExerciseResultType.CORRECT
