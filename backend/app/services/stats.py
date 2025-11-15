"""Service aggregating spaced-repetition and exercise statistics."""

from __future__ import annotations

import math
import uuid
from datetime import date, datetime, time, timedelta, timezone

from app.core.errors import ErrorCode, NotFoundError
from app.models.card import CardRating
from app.models.language_profile import LanguageProfile
from app.models.user import User
from app.repositories.language_profile import LanguageProfileRepository
from app.repositories.stats import ActivityTotals, CardSnapshot, ExerciseSummary, StatsRepository
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


class StatsService:
    """Aggregate daily history into compact REST payloads."""

    PERIOD_WINDOWS: dict[StatsPeriod, timedelta] = {
        StatsPeriod.WEEK: timedelta(days=7),
        StatsPeriod.MONTH: timedelta(days=30),
        StatsPeriod.THREE_MONTHS: timedelta(days=90),
        StatsPeriod.YEAR: timedelta(days=365),
    }

    def __init__(
        self,
        stats_repo: StatsRepository,
        profile_repo: LanguageProfileRepository,
    ) -> None:
        self.stats_repo = stats_repo
        self.profile_repo = profile_repo

    async def get_stats(
        self,
        user: User,
        *,
        profile_id: uuid.UUID | None = None,
        period: StatsPeriod = StatsPeriod.MONTH,
    ) -> StatsResponse:
        """Return aggregated stats for the requested period."""
        profile = await self._resolve_profile(user, profile_id)
        start, end = self._period_window(period)

        card_snapshot = await self.stats_repo.card_snapshot(user.id, profile.id)
        exercise_summary = await self.stats_repo.exercise_summary(
            user.id,
            profile.id,
            start=start,
            end=end,
        )
        activity_data = await self.stats_repo.activity_by_day(
            user.id,
            profile.id,
            start=start,
            end=end,
        )
        total_seconds = sum(
            aggregates.card_duration_seconds + aggregates.exercise_duration_seconds
            for aggregates in activity_data.values()
        )

        activity_entries = self._build_activity_entries(
            activity_data,
            start=start.date() if start else None,
            end=end.date(),
            fill_gaps=start is not None,
        )
        time_total_minutes = int(math.ceil(total_seconds / 60)) if total_seconds else 0
        days_span = self._days_in_period(start, end, activity_entries)
        average_per_day = int(time_total_minutes / days_span) if days_span else 0

        cards = CardStats(
            total=card_snapshot.total,
            new=card_snapshot.new,
            studied=max(card_snapshot.total - card_snapshot.new, 0),
            stats=self._card_ratings(card_snapshot),
        )
        exercises = ExerciseStats(
            total=exercise_summary.total,
            stats=self._exercise_ratings(exercise_summary),
            accuracy=self._exercise_accuracy(exercise_summary),
        )
        streak = StreakSummary(
            current=profile.streak,
            best=profile.best_streak,
            total_days=profile.total_active_days,
        )

        time_stats = TimeStats(
            total_minutes=time_total_minutes,
            average_per_day=average_per_day,
        )

        return StatsResponse(
            profile_id=profile.id,
            language=profile.language,
            current_level=profile.current_level,
            period=period,
            streak=streak,
            cards=cards,
            exercises=exercises,
            time=time_stats,
            activity=activity_entries,
        )

    async def get_streak(
        self,
        user: User,
        *,
        profile_id: uuid.UUID | None = None,
    ) -> StreakResponse:
        """Return expanded streak block with safety window."""
        profile = await self._resolve_profile(user, profile_id)
        latest_activity = await self.stats_repo.last_activity(user.id, profile.id)
        today = datetime.now(tz=timezone.utc).date()
        today_completed = profile.last_activity_date == today

        streak_safe_until = None
        if profile.last_activity_date is not None:
            safe_date = profile.last_activity_date + timedelta(days=1)
            streak_safe_until = datetime.combine(safe_date, time.min, tzinfo=timezone.utc)

        return StreakResponse(
            profile_id=profile.id,
            current_streak=profile.streak,
            best_streak=profile.best_streak,
            total_active_days=profile.total_active_days,
            today_completed=today_completed,
            last_activity=latest_activity,
            streak_safe_until=streak_safe_until,
        )

    async def get_calendar(
        self,
        user: User,
        *,
        profile_id: uuid.UUID | None = None,
        weeks: int = 12,
    ) -> CalendarResponse:
        """Return GitHub-like calendar data for charts."""
        profile = await self._resolve_profile(user, profile_id)
        end = datetime.now(tz=timezone.utc)
        days = max(weeks * 7 - 1, 0)
        start = end - timedelta(days=days)
        activity_data = await self.stats_repo.activity_by_day(
            user.id,
            profile.id,
            start=start,
            end=end,
        )
        entries = self._build_activity_entries(
            activity_data,
            start=start.date(),
            end=end.date(),
            fill_gaps=True,
        )
        return CalendarResponse(data=entries)

    async def _resolve_profile(self, user: User, profile_id: uuid.UUID | None) -> LanguageProfile:
        profile: LanguageProfile | None
        if profile_id is not None:
            profile = await self.profile_repo.get_by_id_for_user(profile_id, user.id)
        else:
            profile = await self.profile_repo.get_active_for_user(user.id)

        if profile is None:
            raise NotFoundError(
                code=ErrorCode.PROFILE_NOT_FOUND,
                message="??????? ?? ??????.",
            )
        return profile

    def _period_window(self, period: StatsPeriod) -> tuple[datetime | None, datetime]:
        end = datetime.now(tz=timezone.utc)
        if period == StatsPeriod.ALL:
            return None, end
        delta = self.PERIOD_WINDOWS.get(period, timedelta(days=30))
        start = end - delta
        return start, end

    def _card_ratings(self, snapshot: CardSnapshot) -> CardRatings:
        know = snapshot.rating_counts.get(CardRating.KNOW.value, 0)
        repeat = snapshot.rating_counts.get(CardRating.REPEAT.value, 0)
        dont_know = snapshot.rating_counts.get(CardRating.DONT_KNOW.value, 0)
        return CardRatings(know=know, repeat=repeat, dont_know=dont_know)

    def _exercise_ratings(self, summary: ExerciseSummary) -> ExerciseRatings:
        return ExerciseRatings(
            correct=summary.correct,
            partial=summary.partial,
            incorrect=summary.incorrect,
        )

    def _exercise_accuracy(self, summary: ExerciseSummary) -> float:
        if summary.total == 0:
            return 0.0
        accuracy = summary.correct / summary.total
        return round(min(max(accuracy, 0.0), 1.0), 2)

    def _build_activity_entries(
        self,
        data: dict[date, ActivityTotals],
        *,
        start: date | None,
        end: date,
        fill_gaps: bool,
    ) -> list[ActivityEntry]:
        if not data and not fill_gaps:
            return []

        entries: list[ActivityEntry] = []
        if fill_gaps and start is not None:
            cursor = start
            while cursor <= end:
                aggregates = data.get(cursor)
                entries.append(self._to_activity_entry(cursor, aggregates))
                cursor += timedelta(days=1)
            return entries

        for day in sorted(data):
            if start and day < start:
                continue
            if day > end:
                continue
            entries.append(self._to_activity_entry(day, data.get(day)))
        return entries

    def _to_activity_entry(self, day: date, aggregates: ActivityTotals | None) -> ActivityEntry:
        cards = aggregates.cards if aggregates else 0
        exercises = aggregates.exercises if aggregates else 0
        time_minutes = aggregates.total_minutes if aggregates else 0
        total_actions = cards + exercises
        level = self._activity_level(total_actions)
        return ActivityEntry(
            date=day,
            activity_level=level,
            cards_studied=cards,
            exercises_completed=exercises,
            time_minutes=time_minutes,
        )

    @staticmethod
    def _activity_level(actions: int) -> ActivityLevel:
        if actions <= 0:
            return ActivityLevel.NONE
        if actions <= 2:
            return ActivityLevel.LOW
        if actions <= 5:
            return ActivityLevel.MEDIUM
        return ActivityLevel.HIGH

    @staticmethod
    def _days_in_period(
        start: datetime | None,
        end: datetime,
        entries: list[ActivityEntry],
    ) -> int:
        if start is not None:
            return max((end.date() - start.date()).days + 1, 1)
        unique_days = {entry.date for entry in entries}
        return max(len(unique_days), 1)


__all__ = ["StatsService"]
