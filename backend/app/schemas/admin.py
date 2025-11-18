"""Schemas and enums for administrative endpoints."""

from __future__ import annotations

from datetime import datetime
from enum import StrEnum
from typing import Literal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, field_validator

from app.schemas.dialog import PaginationMeta


class AdminUserStatus(StrEnum):
    """Available filters for premium/free states."""

    ALL = "all"
    FREE = "free"
    PREMIUM = "premium"


class AdminUserActivity(StrEnum):
    """Activity filters available for the listing endpoint."""

    ACTIVE_7D = "active_7d"
    ACTIVE_30D = "active_30d"
    INACTIVE = "inactive"


class AdminUserSort(StrEnum):
    """Sortable columns for the admin users endpoint."""

    CREATED_AT = "created_at"
    LAST_ACTIVITY = "last_activity"
    CARDS_COUNT = "cards_count"


class AdminMetricsPeriod(StrEnum):
    """Supported aggregation windows for admin metrics."""

    DAYS_7 = "7d"
    DAYS_30 = "30d"
    DAYS_90 = "90d"
    ALL = "all"


class AdminUserResponse(BaseModel):
    """Serialized user row for GET /api/admin/users."""

    id: UUID
    telegram_id: int
    first_name: str
    last_name: str | None = None
    username: str | None = None
    is_premium: bool
    languages: list[str]
    cards_count: int
    exercises_count: int
    streak: int
    last_activity: datetime | None
    created_at: datetime


class AdminUserListResponse(BaseModel):
    """Response wrapper for GET /api/admin/users."""

    data: list[AdminUserResponse]
    pagination: PaginationMeta


class ManualPremiumRequest(BaseModel):
    """Payload for POST /api/admin/users/{user_id}/premium."""

    duration_days: int | Literal["unlimited"] = Field(
        ...,
        description="Number of days to grant premium access or the literal 'unlimited'.",
    )
    reason: str | None = Field(
        default=None,
        min_length=3,
        max_length=200,
        description="Optional reason for the manual grant (stored in audit logs).",
    )

    model_config = ConfigDict(extra="forbid")

    @field_validator("duration_days")
    @classmethod
    def _validate_duration(
        cls,
        value: int | Literal["unlimited"],
    ) -> int | Literal["unlimited"]:
        if isinstance(value, str):
            return value
        if 1 <= value <= 365:
            return value
        msg = "duration_days must be between 1 and 365 days or the literal 'unlimited'."
        raise ValueError(msg)


class ManualPremiumResponse(BaseModel):
    """Response body for manual premium grants."""

    user_id: UUID
    is_premium: bool
    expires_at: datetime | None
    reason: str | None = None


class AdminMetricsUsers(BaseModel):
    """Top-level counters about the user base."""

    total: int
    new: int
    active: int
    premium: int
    premium_percentage: float


class AdminMetricsRetention(BaseModel):
    """Retention ratios for quick health checks."""

    day_7: float
    day_30: float


class AdminMetricsContent(BaseModel):
    """Content inventory stats."""

    total_cards: int
    total_exercises: int
    total_groups: int


class AdminMetricsActivity(BaseModel):
    """Engagement counters per period."""

    messages_sent: int
    cards_studied: int
    exercises_completed: int
    average_session_minutes: float


class AdminMetricsRevenue(BaseModel):
    """Simplified revenue snapshot."""

    total: str
    currency: str
    subscriptions_active: int


class AdminMetricsResponse(BaseModel):
    """Response model for GET /api/admin/metrics."""

    period: AdminMetricsPeriod
    users: AdminMetricsUsers
    retention: AdminMetricsRetention
    content: AdminMetricsContent
    activity: AdminMetricsActivity
    revenue: AdminMetricsRevenue


__all__ = [
    "AdminMetricsActivity",
    "AdminMetricsContent",
    "AdminMetricsPeriod",
    "AdminMetricsResponse",
    "AdminMetricsRetention",
    "AdminMetricsRevenue",
    "AdminMetricsUsers",
    "AdminUserActivity",
    "AdminUserListResponse",
    "AdminUserResponse",
    "AdminUserSort",
    "AdminUserStatus",
    "ManualPremiumRequest",
    "ManualPremiumResponse",
]
