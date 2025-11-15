"""Simple background worker that periodically enqueues streak reminders."""

from __future__ import annotations

import asyncio
import logging

from app.core.config import settings
from app.core.db import AsyncSessionFactory
from app.repositories.language_profile import LanguageProfileRepository
from app.repositories.notification import NotificationRepository, StreakReminderRepository
from app.repositories.stats import StatsRepository
from app.services.notifications import NotificationService

logger = logging.getLogger("app.services.notification_worker")


class NotificationWorker:
    """Periodically triggers the NotificationService streak reminder logic."""

    def __init__(self, interval_seconds: int) -> None:
        self.interval_seconds = interval_seconds
        self._task: asyncio.Task[None] | None = None
        self._stop_event = asyncio.Event()

    def start(self) -> None:
        if self._task is not None:
            return
        self._stop_event.clear()
        self._task = asyncio.create_task(self._run(), name="notification-worker")
        logger.info(
            "Notification worker scheduled",
            extra={"interval_seconds": self.interval_seconds},
        )

    async def shutdown(self) -> None:
        if self._task is None:
            return
        self._stop_event.set()
        await self._task
        self._task = None
        logger.info("Notification worker stopped")

    async def _run(self) -> None:
        while not self._stop_event.is_set():
            try:
                await self._process_cycle()
            except Exception:  # noqa: BLE001
                logger.exception("Notification worker run failed")

            try:
                await asyncio.wait_for(self._stop_event.wait(), timeout=self.interval_seconds)
            except asyncio.TimeoutError:
                continue

    async def _process_cycle(self) -> None:
        async with AsyncSessionFactory() as session:
            service = NotificationService(
                NotificationRepository(session),
                StreakReminderRepository(session),
                LanguageProfileRepository(session),
                StatsRepository(session),
                window_start=settings.streak_reminder_window_start,
                window_end=settings.streak_reminder_window_end,
                retention_days=settings.streak_reminder_retention_days,
            )
            created = await service.process_streak_reminders()
            await session.commit()
            if created:
                logger.info("Generated streak reminders", extra={"count": created})


notification_worker = NotificationWorker(settings.notifications_worker_interval_seconds)

__all__ = ["NotificationWorker", "notification_worker"]
