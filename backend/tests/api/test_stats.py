from __future__ import annotations

import uuid
from datetime import date, datetime, timedelta, timezone
from types import SimpleNamespace

import pytest
from httpx import AsyncClient

from app.api.routes.stats import get_stats_service
from app.core.auth import get_current_user
from app.main import app
from app.schemas.stats import (
    ActivityEntry,
    ActivityLevel,
    CalendarResponse,
    CardRatings,
    CardStats,
    ExerciseRatings,
    ExerciseStats,
    StatsPeriod,
    StatsResponse,
    StreakResponse,
    StreakSummary,
    TimeStats,
)


class StatsServiceStub:
    def __init__(self) -> None:
        self.profile_id = uuid.uuid4()
        self.requested: SimpleNamespace | None = None

    async def get_stats(
        self,
        user: object,
        *,
        profile_id: uuid.UUID | None,
        period: StatsPeriod,
    ) -> StatsResponse:
        self.requested = SimpleNamespace(endpoint="stats", profile_id=profile_id, period=period)
        return StatsResponse(
            profile_id=self.profile_id,
            language="es",
            current_level="A2",
            period=period,
            streak=StreakSummary(current=5, best=10, total_days=40),
            cards=CardStats(
                total=120,
                studied=90,
                new=30,
                stats=CardRatings(know=50, repeat=30, dont_know=10),
            ),
            exercises=ExerciseStats(
                total=20,
                stats=ExerciseRatings(correct=12, partial=5, incorrect=3),
                accuracy=0.6,
            ),
            time=TimeStats(total_minutes=200, average_per_day=10),
            activity=[
                ActivityEntry(
                    date=date.today(),
                    activity_level=ActivityLevel.MEDIUM,
                    cards_studied=3,
                    exercises_completed=2,
                    time_minutes=15,
                )
            ],
        )

    async def get_streak(
        self,
        user: object,
        *,
        profile_id: uuid.UUID | None,
    ) -> StreakResponse:
        self.requested = SimpleNamespace(endpoint="streak", profile_id=profile_id)
        now = datetime.now(tz=timezone.utc)
        return StreakResponse(
            profile_id=self.profile_id,
            current_streak=7,
            best_streak=45,
            total_active_days=120,
            today_completed=True,
            last_activity=now,
            streak_safe_until=now + timedelta(days=1),
        )

    async def get_calendar(
        self,
        user: object,
        *,
        profile_id: uuid.UUID | None,
        weeks: int,
    ) -> CalendarResponse:
        self.requested = SimpleNamespace(endpoint="calendar", profile_id=profile_id, weeks=weeks)
        return CalendarResponse(
            data=[
                ActivityEntry(
                    date=date.today(),
                    activity_level=ActivityLevel.HIGH,
                    cards_studied=5,
                    exercises_completed=3,
                    time_minutes=30,
                )
            ]
        )


@pytest.fixture()
def stats_service_stub() -> StatsServiceStub:
    return StatsServiceStub()


@pytest.fixture(autouse=True)
def _dependency_overrides(stats_service_stub: StatsServiceStub) -> None:
    async def _user_override() -> SimpleNamespace:
        return SimpleNamespace(id=uuid.uuid4())

    async def _service_override() -> StatsServiceStub:
        return stats_service_stub

    app.dependency_overrides[get_current_user] = _user_override
    app.dependency_overrides[get_stats_service] = _service_override
    yield
    app.dependency_overrides.pop(get_current_user, None)
    app.dependency_overrides.pop(get_stats_service, None)


@pytest.mark.asyncio
async def test_get_stats_endpoint_returns_payload(stats_service_stub: StatsServiceStub) -> None:
    async with AsyncClient(app=app, base_url="http://testserver") as client:
        response = await client.get("/api/stats", params={"period": "week"})

    assert response.status_code == 200
    assert response.json()["cards"]["total"] == 120
    assert stats_service_stub.requested.period == StatsPeriod.WEEK


@pytest.mark.asyncio
async def test_get_streak_endpoint_returns_payload(stats_service_stub: StatsServiceStub) -> None:
    async with AsyncClient(app=app, base_url="http://testserver") as client:
        response = await client.get("/api/stats/streak")

    assert response.status_code == 200
    assert response.json()["current_streak"] == 7
    assert stats_service_stub.requested.endpoint == "streak"


@pytest.mark.asyncio
async def test_get_calendar_endpoint_returns_payload(stats_service_stub: StatsServiceStub) -> None:
    async with AsyncClient(app=app, base_url="http://testserver") as client:
        response = await client.get("/api/stats/calendar", params={"weeks": 4})

    assert response.status_code == 200
    assert response.json()["data"][0]["activity_level"] == "high"
    assert stats_service_stub.requested.weeks == 4
