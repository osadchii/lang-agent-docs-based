"""Notification endpoints exposed to the Mini App."""

from __future__ import annotations

from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, Path, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.auth import get_current_user
from app.core.config import settings
from app.core.db import get_session
from app.models.notification import Notification
from app.models.user import User
from app.repositories.language_profile import LanguageProfileRepository
from app.repositories.notification import NotificationRepository, StreakReminderRepository
from app.repositories.stats import StatsRepository
from app.schemas.dialog import PaginationMeta
from app.schemas.notification import (
    NotificationBulkReadResponse,
    NotificationListResponse,
    NotificationReadResponse,
    NotificationResponse,
)
from app.services.notifications import NotificationService

router = APIRouter(tags=["notifications"])


def _serialize(notification: Notification) -> NotificationResponse:
    return NotificationResponse.model_validate(notification)


async def get_notification_service(
    session: Annotated[AsyncSession, Depends(get_session)],
) -> NotificationService:
    return NotificationService(
        NotificationRepository(session),
        StreakReminderRepository(session),
        LanguageProfileRepository(session),
        StatsRepository(session),
        window_start=settings.streak_reminder_window_start,
        window_end=settings.streak_reminder_window_end,
        retention_days=settings.streak_reminder_retention_days,
    )


@router.get(
    "/notifications",
    response_model=NotificationListResponse,
    summary="List notifications for the current user",
)
async def list_notifications(
    unread_only: Annotated[
        bool,
        Query(description="Return only unread notifications."),
    ] = False,
    limit: Annotated[
        int,
        Query(ge=1, le=100, description="Maximum notifications to return."),
    ] = 20,
    offset: Annotated[
        int,
        Query(ge=0, description="Number of notifications to skip."),
    ] = 0,
    user: User = Depends(get_current_user),  # noqa: B008
    service: NotificationService = Depends(get_notification_service),  # noqa: B008
) -> NotificationListResponse:
    result = await service.list_notifications(
        user,
        unread_only=unread_only,
        limit=limit,
        offset=offset,
    )
    data = [_serialize(item) for item in result.notifications]
    has_more = offset + limit < result.total
    pagination = PaginationMeta(
        limit=limit,
        offset=offset,
        count=result.total,
        has_more=has_more,
        next_offset=(offset + limit) if has_more else None,
    )
    return NotificationListResponse(
        data=data,
        pagination=pagination,
        unread_count=result.unread_count,
    )


@router.post(
    "/notifications/{notification_id}/read",
    response_model=NotificationReadResponse,
    summary="Mark a notification as read",
)
async def read_notification(
    notification_id: Annotated[UUID, Path(description="Notification identifier.")],
    user: User = Depends(get_current_user),  # noqa: B008
    service: NotificationService = Depends(get_notification_service),  # noqa: B008
) -> NotificationReadResponse:
    notification = await service.mark_notification_read(user, notification_id)
    await service.session.commit()
    return NotificationReadResponse(id=notification.id, is_read=notification.is_read)


@router.post(
    "/notifications/read-all",
    response_model=NotificationBulkReadResponse,
    summary="Mark all notifications as read",
    status_code=status.HTTP_200_OK,
)
async def read_all_notifications(
    user: User = Depends(get_current_user),  # noqa: B008
    service: NotificationService = Depends(get_notification_service),  # noqa: B008
) -> NotificationBulkReadResponse:
    marked = await service.mark_all_notifications_read(user)
    await service.session.commit()
    return NotificationBulkReadResponse(marked_read=marked)


__all__ = ["get_notification_service", "router"]
