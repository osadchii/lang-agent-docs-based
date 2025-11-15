"""Analytics-focused queries powering the statistics endpoints."""

from __future__ import annotations

import dataclasses
import uuid
from collections import defaultdict
import math
from datetime import date, datetime

from sqlalchemy import Select, func, select
from sqlalchemy.orm import aliased

from app.models.card import Card, CardRating, CardReview, CardStatus
from app.models.deck import Deck
from app.models.exercise import ExerciseHistory, ExerciseResultType
from app.models.language_profile import LanguageProfile
from app.repositories.base import BaseRepository


@dataclasses.dataclass(slots=True)
class CardSnapshot:
    """Aggregate values representing cards for a profile."""

    total: int
    new: int
    rating_counts: dict[str, int]


@dataclasses.dataclass(slots=True)
class ExerciseSummary:
    """Aggregate values representing exercise outcomes."""

    total: int
    correct: int
    partial: int
    incorrect: int


@dataclasses.dataclass(slots=True)
class ActivityTotals:
    """Counts per day used by activity charts."""

    cards: int = 0
    exercises: int = 0
    card_duration_seconds: int = 0
    exercise_duration_seconds: int = 0

    @property
    def total_minutes(self) -> int:
        seconds = self.card_duration_seconds + self.exercise_duration_seconds
        if seconds <= 0:
            return 0
        return int(math.ceil(seconds / 60))


class StatsRepository(BaseRepository[object]):
    """Read-heavy repository exposing aggregate stats queries."""

    async def card_snapshot(self, user_id: uuid.UUID, profile_id: uuid.UUID) -> CardSnapshot:
        """Return total/new counts and rating distribution for cards."""
        stmt: Select[tuple[int, int]] = (
            select(
                func.count(Card.id),
                func.count().filter(Card.status == CardStatus.NEW),
            )
            .select_from(Card)
            .join(Deck, Card.deck_id == Deck.id)
            .join(LanguageProfile, Deck.profile_id == LanguageProfile.id)
            .where(
                LanguageProfile.id == profile_id,
                LanguageProfile.user_id == user_id,
                LanguageProfile.deleted.is_(False),
                Deck.deleted.is_(False),
                Card.deleted.is_(False),
            )
        )
        total_result = await self.session.execute(stmt)
        total, new_count = total_result.one()

        rating_stmt = (
            select(Card.last_rating, func.count())
            .select_from(Card)
            .join(Deck, Card.deck_id == Deck.id)
            .join(LanguageProfile, Deck.profile_id == LanguageProfile.id)
            .where(
                LanguageProfile.id == profile_id,
                LanguageProfile.user_id == user_id,
                LanguageProfile.deleted.is_(False),
                Deck.deleted.is_(False),
                Card.deleted.is_(False),
            )
            .group_by(Card.last_rating)
        )
        rating_rows = await self.session.execute(rating_stmt)
        rating_counts: dict[str, int] = {}
        for rating, count in rating_rows:
            if rating is None:
                continue
            # Persist the string literal value to avoid Enum serialization issues in SQLite.
            if isinstance(rating, CardRating):
                rating_counts[rating.value] = int(count)
            else:
                rating_counts[str(rating)] = int(count)

        return CardSnapshot(
            total=int(total),
            new=int(new_count),
            rating_counts=rating_counts,
        )

    async def exercise_summary(
        self,
        user_id: uuid.UUID,
        profile_id: uuid.UUID,
        *,
        start: datetime | None = None,
        end: datetime | None = None,
    ) -> ExerciseSummary:
        """Return exercise totals (optionally filtered by period)."""
        stmt: Select[tuple[int, int, int, int]] = select(
            func.count(ExerciseHistory.id),
            func.count().filter(ExerciseHistory.result == ExerciseResultType.CORRECT),
            func.count().filter(ExerciseHistory.result == ExerciseResultType.PARTIAL),
            func.count().filter(ExerciseHistory.result == ExerciseResultType.INCORRECT),
        ).where(
            ExerciseHistory.profile_id == profile_id,
            ExerciseHistory.user_id == user_id,
        )
        if start is not None:
            stmt = stmt.where(ExerciseHistory.completed_at >= start)
        if end is not None:
            stmt = stmt.where(ExerciseHistory.completed_at <= end)

        result = await self.session.execute(stmt)
        total, correct, partial, incorrect = result.one()
        return ExerciseSummary(
            total=int(total),
            correct=int(correct),
            partial=int(partial),
            incorrect=int(incorrect),
        )

    async def activity_by_day(
        self,
        user_id: uuid.UUID,
        profile_id: uuid.UUID,
        *,
        start: datetime | None = None,
        end: datetime | None = None,
    ) -> dict[date, ActivityTotals]:
        """Return combined exercise + card review metrics grouped by day."""
        aggregates: dict[date, ActivityTotals] = defaultdict(ActivityTotals)

        exercise_stmt = (
            select(
                func.date(ExerciseHistory.completed_at),
                func.count(),
                func.coalesce(func.sum(ExerciseHistory.duration_seconds), 0),
            )
            .where(
                ExerciseHistory.profile_id == profile_id,
                ExerciseHistory.user_id == user_id,
            )
            .group_by(func.date(ExerciseHistory.completed_at))
        )
        if start is not None:
            exercise_stmt = exercise_stmt.where(ExerciseHistory.completed_at >= start)
        if end is not None:
            exercise_stmt = exercise_stmt.where(ExerciseHistory.completed_at <= end)

        exercise_rows = await self.session.execute(exercise_stmt)
        for day_value, count, duration in exercise_rows:
            day = _normalize_date(day_value)
            item = aggregates[day]
            item.exercises += int(count or 0)
            item.exercise_duration_seconds += int(duration or 0)

        CardAlias = aliased(Card)
        card_stmt = (
            select(
                func.date(CardReview.reviewed_at),
                func.count(),
                func.coalesce(func.sum(CardReview.duration_seconds), 0),
            )
            .select_from(CardReview)
            .join(CardAlias, CardReview.card_id == CardAlias.id)
            .join(Deck, CardAlias.deck_id == Deck.id)
            .join(LanguageProfile, Deck.profile_id == LanguageProfile.id)
            .where(
                CardReview.user_id == user_id,
                LanguageProfile.id == profile_id,
                LanguageProfile.user_id == user_id,
                LanguageProfile.deleted.is_(False),
                Deck.deleted.is_(False),
                CardAlias.deleted.is_(False),
            )
            .group_by(func.date(CardReview.reviewed_at))
        )
        if start is not None:
            card_stmt = card_stmt.where(CardReview.reviewed_at >= start)
        if end is not None:
            card_stmt = card_stmt.where(CardReview.reviewed_at <= end)

        card_rows = await self.session.execute(card_stmt)
        for day_value, count, duration in card_rows:
            day = _normalize_date(day_value)
            item = aggregates[day]
            item.cards += int(count or 0)
            item.card_duration_seconds += int(duration or 0)

        return dict(aggregates)

    async def last_activity(
        self,
        user_id: uuid.UUID,
        profile_id: uuid.UUID,
    ) -> datetime | None:
        """Return the latest timestamp across card reviews and exercises."""
        exercise_stmt = (
            select(func.max(ExerciseHistory.completed_at))
            .where(
                ExerciseHistory.profile_id == profile_id,
                ExerciseHistory.user_id == user_id,
            )
            .limit(1)
        )
        exercise_result = await self.session.execute(exercise_stmt)
        exercise_last: datetime | None = exercise_result.scalar_one_or_none()

        CardAlias = aliased(Card)
        review_stmt = (
            select(func.max(CardReview.reviewed_at))
            .select_from(CardReview)
            .join(CardAlias, CardReview.card_id == CardAlias.id)
            .join(Deck, CardAlias.deck_id == Deck.id)
            .join(LanguageProfile, Deck.profile_id == LanguageProfile.id)
            .where(
                CardReview.user_id == user_id,
                LanguageProfile.id == profile_id,
                LanguageProfile.user_id == user_id,
                LanguageProfile.deleted.is_(False),
                Deck.deleted.is_(False),
                CardAlias.deleted.is_(False),
            )
            .limit(1)
        )
        review_result = await self.session.execute(review_stmt)
        review_last: datetime | None = review_result.scalar_one_or_none()

        if exercise_last and review_last:
            return exercise_last if exercise_last >= review_last else review_last
        return exercise_last or review_last


def _normalize_date(raw: date | datetime | str) -> date:
    """Convert various SQL date representations to date objects."""
    if isinstance(raw, date) and not isinstance(raw, datetime):
        return raw
    if isinstance(raw, datetime):
        return raw.date()
    return date.fromisoformat(str(raw))


__all__ = [
    "ActivityTotals",
    "CardSnapshot",
    "ExerciseSummary",
    "StatsRepository",
]
