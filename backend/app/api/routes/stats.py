"""Statistics endpoints exposing study progress aggregates."""

from __future__ import annotations

from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.auth import get_current_user
from app.core.db import get_session
from app.models.user import User
from app.repositories.language_profile import LanguageProfileRepository
from app.repositories.stats import StatsRepository
from app.schemas.stats import CalendarResponse, StatsPeriod, StatsResponse, StreakResponse
from app.services.stats import StatsService

router = APIRouter(tags=["stats"])


async def get_stats_service(
    session: Annotated[AsyncSession, Depends(get_session)],
) -> StatsService:
    profile_repo = LanguageProfileRepository(session)
    stats_repo = StatsRepository(session)
    return StatsService(stats_repo, profile_repo)


@router.get(
    "/stats",
    response_model=StatsResponse,
    summary="Return aggregated statistics for the current user",
)
async def get_stats(
    profile_id: Annotated[UUID | None, Query(description="Language profile identifier.")] = None,
    period: Annotated[
        StatsPeriod,
        Query(description="Aggregation period."),
    ] = StatsPeriod.MONTH,
    user: User = Depends(get_current_user),  # noqa: B008
    service: StatsService = Depends(get_stats_service),  # noqa: B008
) -> StatsResponse:
    return await service.get_stats(user, profile_id=profile_id, period=period)


@router.get(
    "/stats/streak",
    response_model=StreakResponse,
    summary="Return streak counters and latest activity",
)
async def get_streak(
    profile_id: Annotated[UUID | None, Query(description="Language profile identifier.")] = None,
    user: User = Depends(get_current_user),  # noqa: B008
    service: StatsService = Depends(get_stats_service),  # noqa: B008
) -> StreakResponse:
    return await service.get_streak(user, profile_id=profile_id)


@router.get(
    "/stats/calendar",
    response_model=CalendarResponse,
    summary="Return activity calendar entries for the Mini App charts",
)
async def get_calendar(
    profile_id: Annotated[UUID | None, Query(description="Language profile identifier.")] = None,
    weeks: Annotated[
        int,
        Query(ge=1, le=52, description="Number of weeks to include in the response."),
    ] = 12,
    user: User = Depends(get_current_user),  # noqa: B008
    service: StatsService = Depends(get_stats_service),  # noqa: B008
) -> CalendarResponse:
    return await service.get_calendar(user, profile_id=profile_id, weeks=weeks)


__all__ = ["get_stats_service", "router"]
