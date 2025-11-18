"""Data-intensive queries supporting admin dashboards."""

from __future__ import annotations

import dataclasses
import uuid
from datetime import datetime, timedelta
from typing import Any, Sequence

from sqlalchemy import Select, and_, exists, func, or_, select
from sqlalchemy.orm import aliased
from sqlalchemy.sql.elements import ColumnElement
from sqlalchemy.sql.selectable import Subquery

from app.models.card import CardReview
from app.models.conversation import ConversationMessage, MessageRole
from app.models.deck import Deck
from app.models.exercise import ExerciseHistory
from app.models.group import Group
from app.models.language_profile import LanguageProfile
from app.models.user import User
from app.repositories.base import BaseRepository
from app.schemas.admin import AdminMetricsPeriod, AdminUserActivity, AdminUserSort, AdminUserStatus


@dataclasses.dataclass(slots=True)
class AdminUserRow:
    """Compact container for a user row and aggregated counters."""

    user: User
    cards_count: int
    exercises_count: int
    streak: int


@dataclasses.dataclass(slots=True)
class MetricsSnapshot:
    """Intermediate aggregation structure for admin metrics."""

    total_users: int
    new_users: int
    active_users: int
    premium_users: int
    active_7d: int
    active_30d: int
    total_cards: int
    total_exercises: int
    total_groups: int
    messages_sent: int
    cards_studied: int
    exercises_completed: int
    card_duration_seconds: int
    exercise_duration_seconds: int


class AdminRepository(BaseRepository[User]):
    """Collection of specialized queries for admin analytics."""

    async def list_users(
        self,
        *,
        status: AdminUserStatus,
        activity: AdminUserActivity,
        language: str | None,
        sort: AdminUserSort,
        limit: int,
        offset: int,
        now: datetime,
    ) -> list[AdminUserRow]:
        cards_alias = self._cards_subquery()
        exercises_alias = self._exercises_subquery()
        streak_alias = self._streak_subquery()

        stmt: Select[tuple[User, int, int, int]] = (
            select(
                User,
                func.coalesce(cards_alias.c.cards_count, 0),
                func.coalesce(exercises_alias.c.exercises_count, 0),
                func.coalesce(streak_alias.c.streak, 0),
            )
            .outerjoin(cards_alias, cards_alias.c.user_id == User.id)
            .outerjoin(exercises_alias, exercises_alias.c.user_id == User.id)
            .outerjoin(streak_alias, streak_alias.c.user_id == User.id)
            .where(User.deleted.is_(False))
        )

        stmt = self._apply_filters(
            stmt,
            status=status,
            activity=activity,
            language=language,
            now=now,
        )

        stmt = self._apply_sort(stmt, sort, cards_alias)
        stmt = stmt.limit(limit).offset(offset)

        result = await self.session.execute(stmt)
        rows: list[AdminUserRow] = []
        for user, cards_count, exercises_count, streak in result:
            rows.append(
                AdminUserRow(
                    user=user,
                    cards_count=int(cards_count or 0),
                    exercises_count=int(exercises_count or 0),
                    streak=int(streak or 0),
                )
            )
        return rows

    async def count_users(
        self,
        *,
        status: AdminUserStatus,
        activity: AdminUserActivity,
        language: str | None,
        now: datetime,
    ) -> int:
        stmt: Select[tuple[int]] = select(func.count()).select_from(User)
        stmt = stmt.where(User.deleted.is_(False))
        stmt = self._apply_filters(
            stmt,
            status=status,
            activity=activity,
            language=language,
            now=now,
        )
        result = await self.session.execute(stmt)
        return int(result.scalar_one())

    async def languages_for_users(
        self,
        user_ids: Sequence[uuid.UUID],
    ) -> dict[uuid.UUID, list[str]]:
        """Return a mapping of user_id -> sorted languages."""
        if not user_ids:
            return {}
        stmt = (
            select(LanguageProfile.user_id, LanguageProfile.language)
            .where(
                LanguageProfile.user_id.in_(tuple(user_ids)),
                LanguageProfile.deleted.is_(False),
            )
            .order_by(LanguageProfile.user_id, LanguageProfile.language)
        )
        result = await self.session.execute(stmt)
        mapping: dict[uuid.UUID, list[str]] = {}
        for user_id, language in result:
            mapping.setdefault(user_id, []).append(language)
        return mapping

    async def get_user(self, user_id: uuid.UUID) -> User | None:
        """Fetch a single user by primary key."""
        return await self.session.get(User, user_id)

    async def metrics_snapshot(
        self,
        *,
        now: datetime,
        period: AdminMetricsPeriod,
    ) -> MetricsSnapshot:
        """Compute the metrics aggregates used by the admin dashboard."""
        period_start = self._period_start(now, period)

        total_users = await self._scalar(select(func.count()).where(User.deleted.is_(False)))

        if period_start is not None:
            new_users = await self._scalar(
                select(func.count()).where(
                    User.deleted.is_(False),
                    User.created_at >= period_start,
                )
            )
            active_users = await self._scalar(
                select(func.count()).where(
                    User.deleted.is_(False),
                    User.last_activity.is_not(None),
                    User.last_activity >= period_start,
                )
            )
        else:
            new_users = total_users
            active_users = total_users

        premium_condition = self._premium_condition(now)
        premium_users = await self._scalar(
            select(func.count()).where(User.deleted.is_(False), premium_condition)
        )

        seven_days_ago = now - timedelta(days=7)
        thirty_days_ago = now - timedelta(days=30)
        active_7d = await self._scalar(
            select(func.count()).where(
                User.deleted.is_(False),
                User.last_activity.is_not(None),
                User.last_activity >= seven_days_ago,
            )
        )
        active_30d = await self._scalar(
            select(func.count()).where(
                User.deleted.is_(False),
                User.last_activity.is_not(None),
                User.last_activity >= thirty_days_ago,
            )
        )

        total_cards = await self._scalar(
            select(func.coalesce(func.sum(Deck.cards_count), 0)).where(Deck.deleted.is_(False))
        )
        total_exercises = await self._scalar(select(func.count(ExerciseHistory.id)))
        total_groups = await self._scalar(select(func.count()).where(Group.deleted.is_(False)))

        messages_stmt = select(func.count()).where(
            ConversationMessage.role == MessageRole.USER,
        )
        cards_stmt = select(
            func.count(CardReview.id),
            func.coalesce(func.sum(CardReview.duration_seconds), 0),
        )
        exercises_stmt = select(
            func.count(ExerciseHistory.id),
            func.coalesce(func.sum(ExerciseHistory.duration_seconds), 0),
        )

        if period_start is not None:
            messages_stmt = messages_stmt.where(ConversationMessage.timestamp >= period_start)
            cards_stmt = cards_stmt.where(CardReview.reviewed_at >= period_start)
            exercises_stmt = exercises_stmt.where(ExerciseHistory.completed_at >= period_start)

        messages_sent = await self._scalar(messages_stmt)

        cards_result = await self.session.execute(cards_stmt)
        cards_count, cards_duration = cards_result.one()

        exercises_result = await self.session.execute(exercises_stmt)
        exercises_count, exercises_duration = exercises_result.one()

        return MetricsSnapshot(
            total_users=total_users,
            new_users=new_users,
            active_users=active_users,
            premium_users=premium_users,
            active_7d=active_7d,
            active_30d=active_30d,
            total_cards=total_cards,
            total_exercises=total_exercises,
            total_groups=total_groups,
            messages_sent=messages_sent,
            cards_studied=int(cards_count or 0),
            exercises_completed=int(exercises_count or 0),
            card_duration_seconds=int(cards_duration or 0),
            exercise_duration_seconds=int(exercises_duration or 0),
        )

    def _cards_subquery(self) -> Subquery:
        profile_alias = aliased(LanguageProfile)
        deck_alias = aliased(Deck)
        stmt = (
            select(
                User.id.label("user_id"),
                func.coalesce(func.sum(deck_alias.cards_count), 0).label("cards_count"),
            )
            .outerjoin(
                profile_alias,
                and_(
                    profile_alias.user_id == User.id,
                    profile_alias.deleted.is_(False),
                ),
            )
            .outerjoin(
                deck_alias,
                and_(
                    deck_alias.profile_id == profile_alias.id,
                    deck_alias.deleted.is_(False),
                ),
            )
            .where(User.deleted.is_(False))
            .group_by(User.id)
        )
        return stmt.subquery()

    def _exercises_subquery(self) -> Subquery:
        stmt = (
            select(
                User.id.label("user_id"),
                func.count(ExerciseHistory.id).label("exercises_count"),
            )
            .outerjoin(ExerciseHistory, ExerciseHistory.user_id == User.id)
            .where(User.deleted.is_(False))
            .group_by(User.id)
        )
        return stmt.subquery()

    def _streak_subquery(self) -> Subquery:
        profile_alias = aliased(LanguageProfile)
        stmt = (
            select(
                User.id.label("user_id"),
                func.max(profile_alias.streak).label("streak"),
            )
            .outerjoin(
                profile_alias,
                and_(
                    profile_alias.user_id == User.id,
                    profile_alias.deleted.is_(False),
                ),
            )
            .where(User.deleted.is_(False))
            .group_by(User.id)
        )
        return stmt.subquery()

    def _apply_filters(
        self,
        stmt: Select[Any],
        *,
        status: AdminUserStatus,
        activity: AdminUserActivity,
        language: str | None,
        now: datetime,
    ) -> Select[Any]:
        if status == AdminUserStatus.FREE:
            stmt = stmt.where(~self._premium_condition(now))
        elif status == AdminUserStatus.PREMIUM:
            stmt = stmt.where(self._premium_condition(now))

        if activity == AdminUserActivity.ACTIVE_7D:
            threshold = now - timedelta(days=7)
            stmt = stmt.where(
                User.last_activity.is_not(None),
                User.last_activity >= threshold,
            )
        elif activity == AdminUserActivity.ACTIVE_30D:
            threshold = now - timedelta(days=30)
            stmt = stmt.where(
                User.last_activity.is_not(None),
                User.last_activity >= threshold,
            )
        elif activity == AdminUserActivity.INACTIVE:
            threshold = now - timedelta(days=30)
            stmt = stmt.where(
                or_(
                    User.last_activity.is_(None),
                    User.last_activity < threshold,
                )
            )

        if language:
            lang = language.lower()
            language_exists = (
                select(1)
                .where(
                    LanguageProfile.user_id == User.id,
                    LanguageProfile.deleted.is_(False),
                    func.lower(LanguageProfile.language) == lang,
                )
                .limit(1)
            )
            stmt = stmt.where(exists(language_exists))
        return stmt

    def _apply_sort(
        self,
        stmt: Select[Any],
        sort: AdminUserSort,
        cards_alias: Subquery,
    ) -> Select[Any]:
        if sort == AdminUserSort.LAST_ACTIVITY:
            return stmt.order_by(
                User.last_activity.is_(None),
                User.last_activity.desc(),
                User.created_at.desc(),
            )
        if sort == AdminUserSort.CARDS_COUNT:
            return stmt.order_by(
                cards_alias.c.cards_count.desc(),
                User.created_at.desc(),
            )
        return stmt.order_by(User.created_at.desc())

    def _premium_condition(self, now: datetime) -> ColumnElement[bool]:
        active_expiration = and_(
            User.premium_expires_at.is_not(None),
            User.premium_expires_at > now,
        )
        trial_active = and_(
            User.trial_ends_at.is_not(None),
            User.trial_ends_at > now,
        )
        return or_(User.is_premium.is_(True), active_expiration, trial_active)

    async def _scalar(self, stmt: Select[tuple[int]]) -> int:
        result = await self.session.execute(stmt)
        return int(result.scalar_one() or 0)

    @staticmethod
    def _period_start(now: datetime, period: AdminMetricsPeriod) -> datetime | None:
        if period == AdminMetricsPeriod.ALL:
            return None
        mapping = {
            AdminMetricsPeriod.DAYS_7: timedelta(days=7),
            AdminMetricsPeriod.DAYS_30: timedelta(days=30),
            AdminMetricsPeriod.DAYS_90: timedelta(days=90),
        }
        delta = mapping.get(period)
        if not delta:
            return None
        return now - delta


__all__ = ["AdminRepository", "AdminUserRow", "MetricsSnapshot"]
