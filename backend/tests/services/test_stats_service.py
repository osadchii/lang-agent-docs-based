from __future__ import annotations

import uuid
from datetime import datetime, timedelta, timezone
from types import SimpleNamespace

import pytest
import pytest_asyncio
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.card import Card, CardRating, CardReview, CardStatus
from app.models.deck import Deck
from app.models.exercise import ExerciseResultType, ExerciseType
from app.models.language_profile import LanguageProfile
from app.models.topic import Topic, TopicType
from app.models.user import User
from app.repositories.exercise import ExerciseHistoryRepository
from app.repositories.language_profile import LanguageProfileRepository
from app.repositories.stats import ExerciseSummary, StatsRepository
from app.schemas.stats import ActivityLevel, StatsPeriod
from app.services.stats import StatsService


async def _setup_context(
    db_session: AsyncSession,
    *,
    with_activity: bool,
    with_last_activity: bool,
) -> SimpleNamespace:
    now = datetime.now(tz=timezone.utc)
    user = User(
        id=uuid.uuid4(),
        telegram_id=123,
        first_name="Stats",
        created_at=now,
        updated_at=now,
    )
    profile = LanguageProfile(
        id=uuid.uuid4(),
        user_id=user.id,
        language="es",
        language_name="Spanish",
        current_level="A2",
        target_level="B1",
        goals=["travel"],
        interface_language="ru",
        is_active=True,
        streak=7 if with_activity else 0,
        best_streak=30 if with_activity else 0,
        total_active_days=90 if with_activity else 0,
        last_activity_date=now.date() if with_last_activity else None,
        created_at=now,
        updated_at=now,
    )
    deck = Deck(
        id=uuid.uuid4(),
        profile_id=profile.id,
        name="Core Deck",
        owner_id=user.id,
        is_active=True,
        created_at=now,
        updated_at=now,
    )
    db_session.add_all([user, profile, deck])

    stats_repo = StatsRepository(db_session)
    profile_repo = LanguageProfileRepository(db_session)

    if with_activity:
        topic = Topic(
            id=uuid.uuid4(),
            profile_id=profile.id,
            name="Subjuntivo",
            description="Verb practice",
            type=TopicType.GRAMMAR,
            created_at=now,
            updated_at=now,
        )
        cards = [
            Card(
                id=uuid.uuid4(),
                deck_id=deck.id,
                word="hablar",
                translation="говорить",
                example="Quiero hablar contigo",
                example_translation="Хочу поговорить с тобой",
                lemma="hablar",
                status=CardStatus.NEW,
                interval_days=0,
                next_review=now + timedelta(days=1),
                reviews_count=0,
                ease_factor=2.5,
                created_at=now,
                updated_at=now,
            ),
            Card(
                id=uuid.uuid4(),
                deck_id=deck.id,
                word="comer",
                translation="есть",
                example="Voy a comer",
                example_translation="Я собираюсь поесть",
                lemma="comer",
                status=CardStatus.LEARNING,
                interval_days=2,
                next_review=now + timedelta(days=2),
                reviews_count=3,
                ease_factor=2.4,
                last_rating=CardRating.KNOW,
                created_at=now,
                updated_at=now,
            ),
            Card(
                id=uuid.uuid4(),
                deck_id=deck.id,
                word="vivir",
                translation="жить",
                example="Quiero vivir en Madrid",
                example_translation="Хочу жить в Мадриде",
                lemma="vivir",
                status=CardStatus.REVIEW,
                interval_days=5,
                next_review=now + timedelta(days=5),
                reviews_count=4,
                ease_factor=2.6,
                last_rating=CardRating.REPEAT,
                created_at=now,
                updated_at=now,
            ),
        ]
        reviews = [
            CardReview(
                id=uuid.uuid4(),
                card_id=cards[1].id,
                user_id=user.id,
                rating=CardRating.KNOW,
                interval_before=1,
                interval_after=2,
                duration_seconds=120,
                reviewed_at=now - timedelta(days=1),
            ),
            CardReview(
                id=uuid.uuid4(),
                card_id=cards[2].id,
                user_id=user.id,
                rating=CardRating.REPEAT,
                interval_before=2,
                interval_after=4,
                duration_seconds=60,
                reviewed_at=now - timedelta(days=1),
            ),
        ]
        db_session.add_all([topic, *cards, *reviews])
        await db_session.flush()

        exercise_repo = ExerciseHistoryRepository(db_session)
        attempt_one = await exercise_repo.record_attempt(
            user_id=user.id,
            profile_id=profile.id,
            topic_id=topic.id,
            exercise_type=ExerciseType.FREE_TEXT,
            question="Q1",
            prompt="P1",
            correct_answer="A1",
            user_answer="A1",
            result=ExerciseResultType.CORRECT,
            explanation=None,
            used_hint=False,
            duration_seconds=90,
            metadata={},
        )
        attempt_one.completed_at = now - timedelta(days=1)

        attempt_two = await exercise_repo.record_attempt(
            user_id=user.id,
            profile_id=profile.id,
            topic_id=topic.id,
            exercise_type=ExerciseType.FREE_TEXT,
            question="Q2",
            prompt="P2",
            correct_answer="A2",
            user_answer="A2?",
            result=ExerciseResultType.PARTIAL,
            explanation=None,
            used_hint=True,
            duration_seconds=30,
            metadata={},
        )
        attempt_two.completed_at = now

        await db_session.flush()

    stats_repo = StatsRepository(db_session)
    profile_repo = LanguageProfileRepository(db_session)
    service = StatsService(stats_repo, profile_repo)

    return SimpleNamespace(
        user=user,
        profile=profile,
        service=service,
        now=now,
    )


@pytest_asyncio.fixture()
async def stats_context(db_session: AsyncSession) -> SimpleNamespace:
    return await _setup_context(db_session, with_activity=True, with_last_activity=True)


@pytest_asyncio.fixture()
async def empty_stats_context(db_session: AsyncSession) -> SimpleNamespace:
    return await _setup_context(db_session, with_activity=False, with_last_activity=False)


@pytest.mark.asyncio
async def test_get_stats_returns_aggregated_payload(
    stats_context: SimpleNamespace,
) -> None:
    summary = await stats_context.service.get_stats(
        stats_context.user,
        profile_id=stats_context.profile.id,
        period=StatsPeriod.MONTH,
    )

    assert summary.cards.total == 3
    assert summary.cards.new == 1
    assert summary.cards.studied == 2
    assert summary.cards.stats.know == 1
    assert summary.cards.stats.repeat == 1
    assert summary.exercises.total == 2
    assert summary.exercises.stats.correct == 1
    assert summary.exercises.stats.partial == 1
    assert summary.exercises.accuracy == 0.5
    assert summary.time.total_minutes == 5

    active_day = stats_context.now.date() - timedelta(days=1)
    day_entry = next((entry for entry in summary.activity if entry.date == active_day), None)
    assert day_entry is not None
    assert day_entry.cards_studied == 2
    assert day_entry.exercises_completed == 1


@pytest.mark.asyncio
async def test_get_streak_includes_latest_activity_timestamp(
    stats_context: SimpleNamespace,
) -> None:
    streak = await stats_context.service.get_streak(
        stats_context.user,
        profile_id=stats_context.profile.id,
    )

    assert streak.profile_id == stats_context.profile.id
    assert streak.current_streak == stats_context.profile.streak
    assert streak.today_completed is True
    assert streak.last_activity is not None
    assert streak.streak_safe_until is not None
    assert streak.streak_safe_until.date() == stats_context.profile.last_activity_date + timedelta(
        days=1
    )


@pytest.mark.asyncio
async def test_get_calendar_fills_weeks_with_entries(
    stats_context: SimpleNamespace,
) -> None:
    calendar = await stats_context.service.get_calendar(
        stats_context.user,
        profile_id=stats_context.profile.id,
        weeks=2,
    )

    assert len(calendar.data) == 14
    assert any(entry.cards_studied > 0 for entry in calendar.data)


@pytest.mark.asyncio
async def test_get_stats_without_profile_id_uses_active_profile(
    stats_context: SimpleNamespace,
) -> None:
    summary = await stats_context.service.get_stats(
        stats_context.user,
        period=StatsPeriod.ALL,
    )

    assert summary.profile_id == stats_context.profile.id
    assert len(summary.activity) == 2


@pytest.mark.asyncio
async def test_get_stats_empty_activity_returns_empty_series(
    empty_stats_context: SimpleNamespace,
) -> None:
    summary = await empty_stats_context.service.get_stats(
        empty_stats_context.user,
        period=StatsPeriod.ALL,
    )

    assert summary.cards.total == 0
    assert summary.activity == []
    assert summary.time.total_minutes == 0


@pytest.mark.asyncio
async def test_get_streak_handles_missing_last_activity(
    empty_stats_context: SimpleNamespace,
) -> None:
    streak = await empty_stats_context.service.get_streak(empty_stats_context.user)

    assert streak.today_completed is False
    assert streak.streak_safe_until is None


def test_activity_level_high_branch(stats_context: SimpleNamespace) -> None:
    assert StatsService._activity_level(6) is ActivityLevel.HIGH


def test_exercise_accuracy_handles_zero_total(stats_context: SimpleNamespace) -> None:
    summary = ExerciseSummary(total=0, correct=0, partial=0, incorrect=0)
    assert stats_context.service._exercise_accuracy(summary) == 0.0
