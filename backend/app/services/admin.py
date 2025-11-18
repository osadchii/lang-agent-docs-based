"""Service layer orchestrating admin-specific operations."""

from __future__ import annotations

import dataclasses
import logging
import uuid
from datetime import datetime, timedelta, timezone
from decimal import Decimal
from typing import Literal, Sequence

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.errors import ErrorCode, NotFoundError
from app.models.user import User
from app.repositories.admin import AdminRepository, AdminUserRow, MetricsSnapshot
from app.schemas.admin import AdminMetricsPeriod, AdminUserActivity, AdminUserSort, AdminUserStatus

logger = logging.getLogger("app.services.admin")


@dataclasses.dataclass(slots=True)
class AdminUserView:
    """Serializable representation of an admin user row."""

    id: uuid.UUID
    telegram_id: int
    first_name: str
    last_name: str | None
    username: str | None
    is_premium: bool
    languages: list[str]
    cards_count: int
    exercises_count: int
    streak: int
    last_activity: datetime | None
    created_at: datetime


@dataclasses.dataclass(slots=True)
class AdminUserListResult:
    """Result container for paginated admin user listings."""

    users: list[AdminUserView]
    total: int
    limit: int
    offset: int


@dataclasses.dataclass(slots=True)
class ManualPremiumGrant:
    """Result of granting manual premium access."""

    user_id: uuid.UUID
    is_premium: bool
    expires_at: datetime | None
    reason: str | None


@dataclasses.dataclass(slots=True)
class AdminMetricsUsersBlock:
    total: int
    new: int
    active: int
    premium: int
    premium_percentage: float


@dataclasses.dataclass(slots=True)
class AdminMetricsRetentionBlock:
    day_7: float
    day_30: float


@dataclasses.dataclass(slots=True)
class AdminMetricsContentBlock:
    total_cards: int
    total_exercises: int
    total_groups: int


@dataclasses.dataclass(slots=True)
class AdminMetricsActivityBlock:
    messages_sent: int
    cards_studied: int
    exercises_completed: int
    average_session_minutes: float


@dataclasses.dataclass(slots=True)
class AdminMetricsRevenueBlock:
    total: str
    currency: str
    subscriptions_active: int


@dataclasses.dataclass(slots=True)
class AdminMetricsResult:
    period: AdminMetricsPeriod
    users: AdminMetricsUsersBlock
    retention: AdminMetricsRetentionBlock
    content: AdminMetricsContentBlock
    activity: AdminMetricsActivityBlock
    revenue: AdminMetricsRevenueBlock


class AdminService:
    """Coordinates repositories and aggregates data for admin endpoints."""

    def __init__(self, repository: AdminRepository) -> None:
        self.repository = repository

    @property
    def session(self) -> AsyncSession:
        """Expose the underlying AsyncSession for transactional control."""
        return self.repository.session

    async def list_users(
        self,
        *,
        status: AdminUserStatus,
        activity: AdminUserActivity,
        language: str | None,
        sort: AdminUserSort,
        limit: int,
        offset: int,
    ) -> AdminUserListResult:
        now = datetime.now(tz=timezone.utc)
        normalized_language = language.lower() if language else None
        rows = await self.repository.list_users(
            status=status,
            activity=activity,
            language=normalized_language,
            sort=sort,
            limit=limit,
            offset=offset,
            now=now,
        )
        total = await self.repository.count_users(
            status=status,
            activity=activity,
            language=normalized_language,
            now=now,
        )
        user_ids = [row.user.id for row in rows]
        languages = await self.repository.languages_for_users(user_ids)

        views = [self._to_view(row, languages.get(row.user.id, [])) for row in rows]

        return AdminUserListResult(
            users=views,
            total=total,
            limit=limit,
            offset=offset,
        )

    async def grant_manual_premium(
        self,
        *,
        admin: User,
        user_id: uuid.UUID,
        duration_days: int | Literal["unlimited"],
        reason: str | None,
    ) -> ManualPremiumGrant:
        user = await self.repository.get_user(user_id)
        if user is None or user.deleted:
            raise NotFoundError(
                code=ErrorCode.USER_NOT_FOUND,
                message="?????????? ?? ???????.",
            )

        now = datetime.now(tz=timezone.utc)
        expires_at: datetime | None
        if isinstance(duration_days, str):
            expires_at = None
        else:
            expires_at = now + timedelta(days=duration_days)

        user.is_premium = True
        user.premium_expires_at = expires_at

        await self.session.flush()

        logger.info(
            "Manual premium granted",
            extra={
                "admin_id": str(admin.id),
                "user_id": str(user.id),
                "duration": duration_days,
                "reason": reason,
            },
        )
        return ManualPremiumGrant(
            user_id=user.id,
            is_premium=True,
            expires_at=expires_at,
            reason=reason,
        )

    async def get_metrics(self, period: AdminMetricsPeriod) -> AdminMetricsResult:
        now = datetime.now(tz=timezone.utc)
        snapshot = await self.repository.metrics_snapshot(now=now, period=period)

        premium_percentage = (
            round(
                snapshot.premium_users / snapshot.total_users * 100,
                2,
            )
            if snapshot.total_users
            else 0.0
        )
        users_block = AdminMetricsUsersBlock(
            total=snapshot.total_users,
            new=snapshot.new_users,
            active=snapshot.active_users,
            premium=snapshot.premium_users,
            premium_percentage=premium_percentage,
        )
        retention_block = AdminMetricsRetentionBlock(
            day_7=self._ratio(snapshot.active_7d, snapshot.total_users),
            day_30=self._ratio(snapshot.active_30d, snapshot.total_users),
        )
        content_block = AdminMetricsContentBlock(
            total_cards=snapshot.total_cards,
            total_exercises=snapshot.total_exercises,
            total_groups=snapshot.total_groups,
        )

        avg_minutes = self._average_session_minutes(snapshot)
        activity_block = AdminMetricsActivityBlock(
            messages_sent=snapshot.messages_sent,
            cards_studied=snapshot.cards_studied,
            exercises_completed=snapshot.exercises_completed,
            average_session_minutes=avg_minutes,
        )

        revenue_block = AdminMetricsRevenueBlock(
            total=self._format_currency(Decimal("0.00")),
            currency="EUR",
            subscriptions_active=snapshot.premium_users,
        )

        return AdminMetricsResult(
            period=period,
            users=users_block,
            retention=retention_block,
            content=content_block,
            activity=activity_block,
            revenue=revenue_block,
        )

    def _to_view(self, row: AdminUserRow, languages: Sequence[str]) -> AdminUserView:
        user = row.user
        return AdminUserView(
            id=user.id,
            telegram_id=user.telegram_id,
            first_name=user.first_name,
            last_name=user.last_name,
            username=user.username,
            is_premium=bool(user.is_premium),
            languages=list(languages),
            cards_count=row.cards_count,
            exercises_count=row.exercises_count,
            streak=row.streak,
            last_activity=user.last_activity,
            created_at=user.created_at,
        )

    @staticmethod
    def _ratio(value: int, total: int) -> float:
        if total <= 0:
            return 0.0
        return round(value / total, 2)

    @staticmethod
    def _average_session_minutes(snapshot: MetricsSnapshot) -> float:
        total_duration = snapshot.card_duration_seconds + snapshot.exercise_duration_seconds
        total_events = snapshot.cards_studied + snapshot.exercises_completed
        if total_duration <= 0 or total_events <= 0:
            return 0.0
        minutes = total_duration / total_events / 60
        return round(minutes, 2)

    @staticmethod
    def _format_currency(value: Decimal) -> str:
        return f"{value:.2f}"


__all__ = [
    "AdminMetricsActivityBlock",
    "AdminMetricsContentBlock",
    "AdminMetricsPeriod",
    "AdminMetricsResult",
    "AdminMetricsRetentionBlock",
    "AdminMetricsRevenueBlock",
    "AdminMetricsUsersBlock",
    "AdminService",
    "AdminUserActivity",
    "AdminUserListResult",
    "AdminUserSort",
    "AdminUserStatus",
    "AdminUserView",
    "ManualPremiumGrant",
]
