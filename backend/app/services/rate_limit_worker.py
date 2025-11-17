"""Background worker resetting day-long rate limit counters."""

from __future__ import annotations

import asyncio
import logging
from datetime import datetime, timedelta, timezone

from app.core.config import settings
from app.services.rate_limit import rate_limit_service

logger = logging.getLogger("app.services.rate_limit_worker")


class RateLimitResetWorker:
    """Runs once per day to reset tracked rate limit keys."""

    def __init__(self, reset_hour: int, reset_minute: int) -> None:
        self.reset_hour = max(0, min(reset_hour, 23))
        self.reset_minute = max(0, min(reset_minute, 59))
        self._task: asyncio.Task[None] | None = None
        self._stop_event = asyncio.Event()

    def start(self) -> None:
        if self._task is not None:
            return
        self._stop_event.clear()
        self._task = asyncio.create_task(self._run(), name="rate-limit-reset-worker")
        logger.info(
            "Rate limit reset worker scheduled",
            extra={"hour": self.reset_hour, "minute": self.reset_minute},
        )

    async def shutdown(self) -> None:
        if self._task is None:
            return
        self._stop_event.set()
        await self._task
        self._task = None
        logger.info("Rate limit reset worker stopped")

    async def _run(self) -> None:
        while not self._stop_event.is_set():
            delay = self._seconds_until_window()
            try:
                await asyncio.wait_for(self._stop_event.wait(), timeout=delay)
                continue
            except asyncio.TimeoutError:
                pass

            try:
                cleared = await rate_limit_service.reset_daily_counters()
                if cleared:
                    logger.info("Cleared daily rate limit counters", extra={"cleared": cleared})
            except Exception:  # noqa: BLE001
                logger.exception("Failed to reset rate limit counters")

    def _seconds_until_window(self) -> float:
        now = datetime.now(tz=timezone.utc)
        target = now.replace(
            hour=self.reset_hour,
            minute=self.reset_minute,
            second=0,
            microsecond=0,
        )
        if target <= now:
            target = target + timedelta(days=1)
        return max(1.0, (target - now).total_seconds())


rate_limit_worker = RateLimitResetWorker(
    reset_hour=settings.rate_limit_reset_hour_utc,
    reset_minute=settings.rate_limit_reset_minute_utc,
)

__all__ = ["RateLimitResetWorker", "rate_limit_worker"]
