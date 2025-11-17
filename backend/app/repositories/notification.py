"""Repositories encapsulating notification persistence logic."""

from __future__ import annotations

import uuid
from datetime import date, datetime, timezone
from typing import Any, cast

from sqlalchemy import Select, delete, func, select, update

from app.models.notification import Notification, StreakReminder
from app.repositories.base import BaseRepository


class NotificationRepository(BaseRepository[Notification]):
    """Read/write helpers for the notifications table."""

    async def list_for_user(
        self,
        user_id: uuid.UUID,
        *,
        unread_only: bool = False,
        limit: int = 50,
        offset: int = 0,
    ) -> tuple[list[Notification], int]:
        filters = [Notification.user_id == user_id]
        if unread_only:
            filters.append(Notification.is_read.is_(False))

        stmt: Select[tuple[Notification]] = (
            select(Notification)
            .where(*filters)
            .order_by(Notification.created_at.desc())
            .limit(limit)
            .offset(offset)
        )
        result = await self.session.execute(stmt)
        items = list(result.scalars())

        count_stmt = select(func.count()).where(*filters)
        total_result = await self.session.execute(count_stmt)
        total = int(total_result.scalar_one())
        return items, total

    async def count_unread(self, user_id: uuid.UUID) -> int:
        stmt = select(func.count()).where(
            Notification.user_id == user_id,
            Notification.is_read.is_(False),
        )
        result = await self.session.execute(stmt)
        return int(result.scalar_one())

    async def get_for_user(
        self,
        notification_id: uuid.UUID,
        user_id: uuid.UUID,
    ) -> Notification | None:
        stmt = select(Notification).where(
            Notification.id == notification_id,
            Notification.user_id == user_id,
        )
        result = await self.session.execute(stmt)
        return result.scalar_one_or_none()

    async def mark_as_read(self, notification: Notification) -> Notification:
        if not notification.is_read:
            notification.is_read = True
            notification.read_at = datetime.now(tz=timezone.utc)
            await self.session.flush()
        await self.session.refresh(notification)
        return notification

    async def mark_all_as_read(self, user_id: uuid.UUID) -> int:
        stmt = (
            update(Notification)
            .where(Notification.user_id == user_id, Notification.is_read.is_(False))
            .values(is_read=True, read_at=datetime.now(tz=timezone.utc))
        )
        result = await self.session.execute(stmt)
        rowcount = cast(Any, result).rowcount
        return int(rowcount or 0)


class StreakReminderRepository(BaseRepository[StreakReminder]):
    """Audit helper controlling daily streak reminders."""

    async def was_sent_on(
        self,
        user_id: uuid.UUID,
        profile_id: uuid.UUID,
        sent_date: date,
    ) -> bool:
        stmt = select(func.count()).where(
            StreakReminder.user_id == user_id,
            StreakReminder.profile_id == profile_id,
            StreakReminder.sent_date == sent_date,
        )
        result = await self.session.execute(stmt)
        return bool(result.scalar_one())

    async def log_sent(
        self,
        user_id: uuid.UUID,
        profile_id: uuid.UUID,
        sent_date: date,
        *,
        sent_at: datetime | None = None,
    ) -> StreakReminder:
        reminder = StreakReminder(
            user_id=user_id,
            profile_id=profile_id,
            sent_date=sent_date,
            sent_at=sent_at or datetime.now(tz=timezone.utc),
        )
        await self.add(reminder)
        return reminder

    async def cleanup_before(self, cutoff: date) -> int:
        stmt = delete(StreakReminder).where(StreakReminder.sent_date < cutoff)
        result = await self.session.execute(stmt)
        rowcount = cast(Any, result).rowcount
        return int(rowcount or 0)


__all__ = ["NotificationRepository", "StreakReminderRepository"]
