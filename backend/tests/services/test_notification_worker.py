from __future__ import annotations

import asyncio

import pytest

from app.services.notification_worker import NotificationWorker


class _DummySession:
    def __init__(self, events: list[str]) -> None:
        self.events = events

    async def __aenter__(self) -> "_DummySession":
        self.events.append("enter")
        return self

    async def __aexit__(self, *exc: object) -> None:
        self.events.append("exit")

    async def commit(self) -> None:
        self.events.append("commit")


class _DummyService:
    def __init__(self, *args, **kwargs) -> None:  # noqa: ANN002, ANN003
        self.events = kwargs.get("events")

    async def process_streak_reminders(self) -> int:
        if isinstance(self.events, list):
            self.events.append("process")
        return 1


@pytest.mark.asyncio
async def test_process_cycle_commits_and_logs(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    events: list[str] = []

    monkeypatch.setattr(
        "app.services.notification_worker.AsyncSessionFactory",
        lambda: _DummySession(events),
    )
    monkeypatch.setattr(
        "app.services.notification_worker.NotificationService",
        lambda *args, **kwargs: _DummyService(*args, events=events, **kwargs),
    )

    worker = NotificationWorker(interval_seconds=1)
    await worker._process_cycle()

    assert "process" in events
    assert "commit" in events


@pytest.mark.asyncio
async def test_notification_worker_start_and_shutdown(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    calls: list[str] = []

    class FastWorker(NotificationWorker):
        async def _process_cycle(self) -> None:
            calls.append("cycle")
            await asyncio.sleep(0)

    worker = FastWorker(interval_seconds=0.01)
    worker.start()
    await asyncio.sleep(0.05)
    await worker.shutdown()

    assert calls, "background loop should run at least once"
