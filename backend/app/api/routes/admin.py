"""Administrative API endpoints for dashboards and manual actions."""

from __future__ import annotations

import dataclasses
from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.auth import require_admin
from app.core.db import get_session
from app.models.user import User
from app.repositories.admin import AdminRepository
from app.schemas.admin import (
    AdminMetricsActivity,
    AdminMetricsContent,
    AdminMetricsPeriod,
    AdminMetricsResponse,
    AdminMetricsRetention,
    AdminMetricsRevenue,
    AdminMetricsUsers,
    AdminUserActivity,
    AdminUserListResponse,
    AdminUserResponse,
    AdminUserSort,
    AdminUserStatus,
    ManualPremiumRequest,
    ManualPremiumResponse,
)
from app.schemas.dialog import PaginationMeta
from app.services.admin import AdminService, AdminUserListResult

router = APIRouter(prefix="/admin", tags=["admin"])


async def get_admin_service(
    session: Annotated[AsyncSession, Depends(get_session)],
) -> AdminService:
    """Wire repositories into the admin service."""
    return AdminService(AdminRepository(session))


AdminServiceDep = Annotated[AdminService, Depends(get_admin_service)]
AdminUserDep = Annotated[User, Depends(require_admin)]


@router.get(
    "/users",
    response_model=AdminUserListResponse,
    summary="List users for the admin dashboard",
)
async def list_users(
    *,
    status: Annotated[AdminUserStatus, Query()] = AdminUserStatus.ALL,
    activity: Annotated[AdminUserActivity, Query()] = AdminUserActivity.ACTIVE_30D,
    language: Annotated[
        str | None,
        Query(
            default=None,
            min_length=2,
            max_length=10,
            description="Filter by ISO language.",
        ),
    ] = None,
    sort: Annotated[AdminUserSort, Query()] = AdminUserSort.CREATED_AT,
    limit: Annotated[int, Query(ge=1, le=200)] = 50,
    offset: Annotated[int, Query(ge=0)] = 0,
    admin: AdminUserDep,  # noqa: B008
    service: AdminServiceDep,  # noqa: B008
) -> AdminUserListResponse:
    _ = admin  # appease linters (the dependency ensures authorization)
    result = await service.list_users(
        status=status,
        activity=activity,
        language=language,
        sort=sort,
        limit=limit,
        offset=offset,
    )
    data = [AdminUserResponse(**dataclasses.asdict(user)) for user in result.users]
    pagination = _pagination_meta(result)
    return AdminUserListResponse(data=data, pagination=pagination)


@router.get(
    "/metrics",
    response_model=AdminMetricsResponse,
    summary="Return aggregated admin metrics",
)
async def get_metrics(
    *,
    period: Annotated[AdminMetricsPeriod, Query()] = AdminMetricsPeriod.DAYS_30,
    admin: AdminUserDep,  # noqa: B008
    service: AdminServiceDep,  # noqa: B008
) -> AdminMetricsResponse:
    _ = admin
    snapshot = await service.get_metrics(period)
    return AdminMetricsResponse(
        period=snapshot.period,
        users=AdminMetricsUsers(**dataclasses.asdict(snapshot.users)),
        retention=AdminMetricsRetention(**dataclasses.asdict(snapshot.retention)),
        content=AdminMetricsContent(**dataclasses.asdict(snapshot.content)),
        activity=AdminMetricsActivity(**dataclasses.asdict(snapshot.activity)),
        revenue=AdminMetricsRevenue(**dataclasses.asdict(snapshot.revenue)),
    )


@router.post(
    "/users/{user_id}/premium",
    response_model=ManualPremiumResponse,
    summary="Manually grant premium to a user",
)
async def grant_manual_premium(
    user_id: UUID,
    payload: ManualPremiumRequest,
    admin: AdminUserDep,  # noqa: B008
    service: AdminServiceDep,  # noqa: B008
) -> ManualPremiumResponse:
    grant = await service.grant_manual_premium(
        admin=admin,
        user_id=user_id,
        duration_days=payload.duration_days,
        reason=payload.reason,
    )
    await service.session.commit()
    return ManualPremiumResponse(**dataclasses.asdict(grant))


def _pagination_meta(result: AdminUserListResult) -> PaginationMeta:
    has_more = result.offset + result.limit < result.total
    return PaginationMeta(
        limit=result.limit,
        offset=result.offset,
        count=result.total,
        has_more=has_more,
        next_offset=(result.offset + result.limit) if has_more else None,
    )


__all__ = ["get_admin_service", "router"]
