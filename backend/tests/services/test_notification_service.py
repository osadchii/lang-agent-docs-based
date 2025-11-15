from __future__ import annotations

import uuid
from datetime import datetime, timedelta, timezone
from zoneinfo import ZoneInfo

import pytest
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.errors import NotFoundError
from app.models.exercise import ExerciseHistory, ExerciseResultType, ExerciseType
from app.models.language_profile import LanguageProfile
from app.models.notification import Notification, NotificationType, StreakReminder
from app.models.topic import Topic, TopicType
from app.models.user import User
from app.repositories.language_profile import LanguageProfileRepository
from app.repositories.notification import NotificationRepository, StreakReminderRepository
from app.repositories.stats import StatsRepository
from app.services.notifications import NotificationService


def _build_user() -> User:
    return User(
        id=uuid.uuid4(),
        telegram_id=123456,
        first_name="Tester",
        last_name="User",
        username="tester",
        is_premium=False,
        is_admin=False,
        timezone="UTC",
    )


def _build_profile(user: User, *, streak: int = 5) -> LanguageProfile:
    return LanguageProfile(
        id=uuid.uuid4(),
        user_id=user.id,
        language="es",
        language_name="Испанский",
        current_level="A2",
        target_level="B1",
        goals=["travel"],
        interface_language="ru",
        is_active=True,
        streak=streak,
        best_streak=streak,
        total_active_days=streak,
    )


def _build_topic(profile: LanguageProfile, owner: User) -> Topic:
    return Topic(
        id=uuid.uuid4(),
        profile_id=profile.id,
        name="Travel",
        description=None,
        type=TopicType.GRAMMAR,
        owner_id=owner.id,
        is_active=False,
    )


def _service(
    db_session: AsyncSession,
    *,
    window_start: int = 0,
    window_end: int = 23,
    retention_days: int = 1,
) -> NotificationService:
    return NotificationService(
        NotificationRepository(db_session),
        StreakReminderRepository(db_session),
        LanguageProfileRepository(db_session),
        StatsRepository(db_session),
        window_start=window_start,
        window_end=window_end,
        retention_days=retention_days,
    )


@pytest.mark.asyncio
async def test_list_notifications_returns_counts(db_session: AsyncSession) -> None:
    user = _build_user()
    db_session.add(user)
    await db_session.commit()

    repo = NotificationRepository(db_session)
    await repo.add(
        Notification(
            user_id=user.id,
            type=NotificationType.STREAK_REMINDER,
            title="title",
            message="msg",
            data={"streak": 3},
        )
    )
    await db_session.commit()

    result = await _service(db_session).list_notifications(user)

    assert result.total == 1
    assert result.unread_count == 1


@pytest.mark.asyncio
async def test_mark_notification_read_raises_for_unknown_id(
    db_session: AsyncSession,
) -> None:
    user = _build_user()
    db_session.add(user)
    await db_session.commit()

    service = _service(db_session)
    with pytest.raises(NotFoundError):
        await service.mark_notification_read(user, uuid.uuid4())


@pytest.mark.asyncio
async def test_mark_notification_read_updates_entity(db_session: AsyncSession) -> None:
    user = _build_user()
    db_session.add(user)
    await db_session.commit()

    repo = NotificationRepository(db_session)
    notification = Notification(
        user_id=user.id,
        type=NotificationType.STREAK_REMINDER,
        title="Reminder",
        message="Message",
        data={"streak": 2},
    )
    await repo.add(notification)
    await db_session.commit()

    service = _service(db_session)
    marked = await service.mark_notification_read(user, notification.id)
    assert marked.is_read is True
    assert marked.read_at is not None


@pytest.mark.asyncio
async def test_mark_all_notifications_read_returns_count(
    db_session: AsyncSession,
) -> None:
    user = _build_user()
    db_session.add(user)
    await db_session.commit()
    repo = NotificationRepository(db_session)
    first = Notification(
        user_id=user.id,
        type=NotificationType.STREAK_REMINDER,
        title="First",
        message="Msg",
        data={},
    )
    await repo.add(first)
    already_read = Notification(
        user_id=user.id,
        type=NotificationType.STREAK_REMINDER,
        title="Second",
        message="Msg",
        data={},
        is_read=True,
    )
    db_session.add(already_read)
    await db_session.commit()

    service = _service(db_session)
    total = await service.mark_all_notifications_read(user)
    assert total == 1


@pytest.mark.asyncio
async def test_process_streak_reminders_creates_records(
    db_session: AsyncSession,
) -> None:
    user = _build_user()
    profile = _build_profile(user, streak=4)
    db_session.add_all([user, profile])
    await db_session.commit()

    service = _service(db_session)
    created = await service.process_streak_reminders(
        current_time=datetime(2025, 1, 8, 18, tzinfo=timezone.utc)
    )

    assert created == 1
    notifications, total = await NotificationRepository(db_session).list_for_user(user.id)
    assert total == 1
    assert notifications[0].data["streak"] == 4
    reminders = await db_session.execute(select(StreakReminder))
    assert len(reminders.scalars().all()) == 1


@pytest.mark.asyncio
async def test_process_streak_reminders_skips_when_activity_exists(
    db_session: AsyncSession,
) -> None:
    user = _build_user()
    profile = _build_profile(user)
    topic = _build_topic(profile, user)
    db_session.add_all([user, profile, topic])
    await db_session.commit()

    exercise = ExerciseHistory(
        id=uuid.uuid4(),
        user_id=user.id,
        topic_id=topic.id,
        profile_id=profile.id,
        type=ExerciseType.FREE_TEXT,
        question="Q",
        prompt="P",
        correct_answer="A",
        user_answer="A",
        result=ExerciseResultType.CORRECT,
        explanation=None,
        details={},
        completed_at=datetime(2025, 1, 8, 10, tzinfo=timezone.utc),
    )
    db_session.add(exercise)
    await db_session.commit()

    service = _service(db_session)
    created = await service.process_streak_reminders(
        current_time=datetime(2025, 1, 8, 18, tzinfo=timezone.utc)
    )

    assert created == 0
    _, total = await NotificationRepository(db_session).list_for_user(user.id)
    assert total == 0


def test_session_property_exposes_repo_session(db_session: AsyncSession) -> None:
    service = _service(db_session)
    assert service.session is NotificationRepository(db_session).session


def test_resolve_timezone_uses_fallback(db_session: AsyncSession) -> None:
    service = _service(db_session)
    tz = service._resolve_timezone("Nowhere/Invalid")  # type: ignore[attr-defined]
    assert isinstance(tz, ZoneInfo)
    assert tz.key == "UTC"


def test_within_window_handles_wraparound(db_session: AsyncSession) -> None:
    service = _service(db_session, window_start=22, window_end=6)
    late = datetime(2025, 1, 8, 22, tzinfo=timezone.utc)
    early = datetime(2025, 1, 9, 4, tzinfo=timezone.utc)
    assert service._within_window(late) is True  # type: ignore[attr-defined]
    assert service._within_window(early) is True  # type: ignore[attr-defined]


@pytest.mark.asyncio
async def test_cleanup_old_reminders_removes_rows(db_session: AsyncSession) -> None:
    user = _build_user()
    profile = _build_profile(user)
    db_session.add_all([user, profile])
    await db_session.commit()

    repo = StreakReminderRepository(db_session)
    old_date = datetime.now(tz=timezone.utc).date() - timedelta(days=5)
    await repo.log_sent(user.id, profile.id, old_date)

    service = _service(db_session, retention_days=1)
    await service._cleanup_old_reminders(datetime.now(tz=timezone.utc).date())

    assert await repo.was_sent_on(user.id, profile.id, old_date) is False
