from __future__ import annotations

import uuid
from datetime import datetime, timedelta, timezone
from unittest.mock import AsyncMock

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.exercise import ExerciseResultType, ExerciseType
from app.models.language_profile import LanguageProfile
from app.models.topic import Topic, TopicType
from app.models.user import User
from app.repositories.exercise import ExerciseHistoryRepository
from app.repositories.language_profile import LanguageProfileRepository
from app.repositories.topic import TopicRepository
from app.services.exercise import ExerciseService


def _build_user() -> User:
    return User(
        id=uuid.uuid4(),
        telegram_id=111111,
        first_name="Exercise",
        last_name=None,
        username="exercise-user",
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


def _build_topic(profile: LanguageProfile) -> Topic:
    return Topic(
        id=uuid.uuid4(),
        profile_id=profile.id,
        name="Pret�rito Perfecto",
        description="??????????",
        type=TopicType.GRAMMAR,
    )


@pytest.mark.asyncio
async def test_determine_difficulty_uses_recent_accuracy(db_session: AsyncSession) -> None:
    user = _build_user()
    profile = _build_profile(user)
    topic = _build_topic(profile)
    db_session.add_all([user, profile, topic])
    await db_session.commit()

    history_repo = ExerciseHistoryRepository(db_session)
    topic_repo = TopicRepository(db_session)
    profile_repo = LanguageProfileRepository(db_session)
    llm_stub = AsyncMock()
    cache_stub = AsyncMock()
    service = ExerciseService(history_repo, topic_repo, profile_repo, llm_stub, cache_stub)

    # Insert mostly incorrect attempts -> should be "easy"
    tick = 0
    for _ in range(3):
        entry = await history_repo.record_attempt(
            user_id=user.id,
            profile_id=profile.id,
            topic_id=topic.id,
            exercise_type=ExerciseType.FREE_TEXT,
            question="Q",
            prompt="P",
            correct_answer="A",
            user_answer="B",
            result=ExerciseResultType.INCORRECT,
            explanation=None,
            used_hint=False,
            duration_seconds=None,
            metadata={},
        )
        entry.completed_at = datetime.now(tz=timezone.utc) + timedelta(seconds=tick)
        tick += 1

    difficulty = await service._determine_difficulty(topic.id)
    assert difficulty == "easy"

    # Add correct attempts to push accuracy high -> "hard"
    for _ in range(10):
        entry = await history_repo.record_attempt(
            user_id=user.id,
            profile_id=profile.id,
            topic_id=topic.id,
            exercise_type=ExerciseType.FREE_TEXT,
            question="Q",
            prompt="P",
            correct_answer="A",
            user_answer="A",
            result=ExerciseResultType.CORRECT,
            explanation=None,
            used_hint=False,
            duration_seconds=None,
            metadata={},
        )
        entry.completed_at = datetime.now(tz=timezone.utc) + timedelta(seconds=tick)
        tick += 1

    difficulty = await service._determine_difficulty(topic.id)
    assert difficulty == "hard"
