"""Notification domain service and streak reminder orchestration."""

from __future__ import annotations

import logging
import uuid
from dataclasses import dataclass
from datetime import date, datetime, timedelta, timezone
from zoneinfo import ZoneInfo

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.errors import ErrorCode, NotFoundError
from app.models.language_profile import LanguageProfile
from app.models.notification import Notification, NotificationType
from app.models.user import User
from app.repositories.language_profile import LanguageProfileRepository
from app.repositories.notification import NotificationRepository, StreakReminderRepository
from app.repositories.stats import StatsRepository

logger = logging.getLogger("app.services.notifications")


@dataclass(slots=True)
class NotificationListResult:
    """Container used by the API layer when serializing notifications."""

    notifications: list[Notification]
    total: int
    unread_count: int


class NotificationService:
    """High-level notification operations plus scheduled reminder generation."""

    def __init__(
        self,
        notification_repo: NotificationRepository,
        reminder_repo: StreakReminderRepository,
        profile_repo: LanguageProfileRepository,
        stats_repo: StatsRepository,
        *,
        window_start: int = 17,
        window_end: int = 19,
        retention_days: int = 7,
    ) -> None:
        self.notification_repo = notification_repo
        self.reminder_repo = reminder_repo
        self.profile_repo = profile_repo
        self.stats_repo = stats_repo
        self.window_start = window_start
        self.window_end = window_end
        self.retention_days = retention_days

    @property
    def session(self) -> AsyncSession:
        """Expose the shared AsyncSession instance."""
        return self.notification_repo.session

    async def list_notifications(
        self,
        user: User,
        *,
        unread_only: bool = False,
        limit: int = 20,
        offset: int = 0,
    ) -> NotificationListResult:
        """Return a filtered/paginated notification list plus unread counters."""
        notifications, total = await self.notification_repo.list_for_user(
            user.id,
            unread_only=unread_only,
            limit=limit,
            offset=offset,
        )
        unread = await self.notification_repo.count_unread(user.id)
        return NotificationListResult(
            notifications=notifications,
            total=total,
            unread_count=unread,
        )

    async def mark_notification_read(self, user: User, notification_id: uuid.UUID) -> Notification:
        """Mark a single notification as read."""
        notification = await self.notification_repo.get_for_user(notification_id, user.id)
        if notification is None:
            raise NotFoundError(
                code=ErrorCode.NOTIFICATION_NOT_FOUND,
                message="???????????? ?? ????????.",
            )
        return await self.notification_repo.mark_as_read(notification)

    async def mark_all_notifications_read(self, user: User) -> int:
        """Mark all notifications belonging to the user as read."""
        return await self.notification_repo.mark_all_as_read(user.id)

    async def process_streak_reminders(
        self,
        *,
        current_time: datetime | None = None,
    ) -> int:
        """Generate streak reminders for users that have not studied today."""
        now = current_time or datetime.now(tz=timezone.utc)
        created = 0

        await self._cleanup_old_reminders(now.date())

        profiles = await self.profile_repo.list_active_with_users()
        for profile in profiles:
            user = profile.user
            if user is None:
                continue
            tz = self._resolve_timezone(user.timezone)
            local_time = now.astimezone(tz)

            if not self._within_window(local_time):
                continue
            if profile.streak <= 0:
                continue

            local_date = local_time.date()
            already_sent = await self.reminder_repo.was_sent_on(user.id, profile.id, local_date)
            if already_sent:
                continue

            if await self._has_activity_today(user.id, profile.id, tz, local_date):
                continue

            notification = Notification(
                user_id=user.id,
                type=NotificationType.STREAK_REMINDER,
                title="Не потеряйте стрик!",
                message=self._build_streak_message(profile),
                data={
                    "profile_id": str(profile.id),
                    "language": profile.language,
                    "language_name": profile.language_name,
                    "streak": profile.streak,
                },
            )
            await self.notification_repo.add(notification)
            await self.reminder_repo.log_sent(
                user.id,
                profile.id,
                local_date,
                sent_at=now,
            )
            created += 1
        return created

    async def _has_activity_today(
        self,
        user_id: uuid.UUID,
        profile_id: uuid.UUID,
        timezone_obj: ZoneInfo,
        day: date,
    ) -> bool:
        last_activity = await self.stats_repo.last_activity(user_id, profile_id)
        if last_activity is None:
            return False
        return last_activity.astimezone(timezone_obj).date() >= day

    def _resolve_timezone(self, tz_name: str | None) -> ZoneInfo:
        if tz_name:
            try:
                return ZoneInfo(tz_name)
            except Exception:  # noqa: BLE001
                logger.warning(
                    "Unknown timezone for user, falling back to UTC",
                    extra={"tz": tz_name},
                )
        return ZoneInfo("UTC")

    def _within_window(self, local_time: datetime) -> bool:
        hour = local_time.hour
        if self.window_start <= self.window_end:
            return self.window_start <= hour < self.window_end
        # In case of inverted window (e.g. overnight reminders)
        return hour >= self.window_start or hour < self.window_end

    def _build_streak_message(self, profile: LanguageProfile) -> str:
        return (
            f"У вас {profile.streak} дней подряд обучения. "
            "Выполните хотя бы одно задание сегодня, чтобы не потерять прогресс!"
        )

    async def _cleanup_old_reminders(self, today: date) -> None:
        if self.retention_days <= 0:
            return
        cutoff = today - timedelta(days=self.retention_days)
        removed = await self.reminder_repo.cleanup_before(cutoff)
        if removed:
            logger.info("Removed stale streak reminder entries", extra={"removed": removed})


__all__ = ["NotificationListResult", "NotificationService"]
