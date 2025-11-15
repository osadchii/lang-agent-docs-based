"""Schemas describing notification payloads."""

from __future__ import annotations

from datetime import datetime
from typing import Any
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field

from app.models.notification import NotificationType
from app.schemas.dialog import PaginationMeta


class NotificationResponse(BaseModel):
    """Single notification item returned by GET /api/notifications."""

    id: UUID
    type: NotificationType
    title: str
    message: str
    data: dict[str, Any]
    is_read: bool
    created_at: datetime
    read_at: datetime | None

    model_config = ConfigDict(from_attributes=True)


class NotificationListResponse(BaseModel):
    """Paginated notification list."""

    data: list[NotificationResponse]
    pagination: PaginationMeta
    unread_count: int


class NotificationReadResponse(BaseModel):
    """Minimal response payload after marking a notification as read."""

    id: UUID
    is_read: bool


class NotificationBulkReadResponse(BaseModel):
    """Payload returned by POST /api/notifications/read-all."""

    marked_read: int = Field(ge=0)


__all__ = [
    "NotificationBulkReadResponse",
    "NotificationListResponse",
    "NotificationReadResponse",
    "NotificationResponse",
]
