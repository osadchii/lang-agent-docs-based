"""Pydantic schemas for aggregated statistics endpoints."""

from __future__ import annotations

import enum
import uuid
from datetime import date, datetime

from pydantic import BaseModel, Field


class StatsPeriod(str, enum.Enum):
    """Supported time ranges for statistics."""

    WEEK = "week"
    MONTH = "month"
    THREE_MONTHS = "3months"
    YEAR = "year"
    ALL = "all"


class ActivityLevel(str, enum.Enum):
    """Qualitative bucket for daily workload."""

    NONE = "none"
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"


class StreakSummary(BaseModel):
    """Short streak block embedded into the stats response."""

    current: int = Field(ge=0)
    best: int = Field(ge=0)
    total_days: int = Field(ge=0)


class CardRatings(BaseModel):
    """Distribution of spaced-repetition ratings."""

    know: int = Field(ge=0, default=0)
    repeat: int = Field(ge=0, default=0)
    dont_know: int = Field(ge=0, default=0)


class CardStats(BaseModel):
    """Snapshot of card counts."""

    total: int = Field(ge=0)
    studied: int = Field(ge=0)
    new: int = Field(ge=0)
    stats: CardRatings


class ExerciseRatings(BaseModel):
    """Distribution of LLM exercise outcomes."""

    correct: int = Field(ge=0, default=0)
    partial: int = Field(ge=0, default=0)
    incorrect: int = Field(ge=0, default=0)


class ExerciseStats(BaseModel):
    """Summary of completed exercises."""

    total: int = Field(ge=0)
    stats: ExerciseRatings
    accuracy: float = Field(ge=0.0, le=1.0)


class TimeStats(BaseModel):
    """Aggregate of time spent studying."""

    total_minutes: int = Field(ge=0)
    average_per_day: int = Field(ge=0)


class ActivityEntry(BaseModel):
    """Single day entry for activity charts/calendars."""

    date: date
    activity_level: ActivityLevel
    cards_studied: int = Field(ge=0)
    exercises_completed: int = Field(ge=0)
    time_minutes: int = Field(ge=0)


class StatsResponse(BaseModel):
    """Payload returned by GET /api/stats."""

    profile_id: uuid.UUID
    language: str
    current_level: str
    period: StatsPeriod
    streak: StreakSummary
    cards: CardStats
    exercises: ExerciseStats
    time: TimeStats
    activity: list[ActivityEntry]


class StreakResponse(BaseModel):
    """Detailed streak payload returned by GET /api/stats/streak."""

    profile_id: uuid.UUID
    current_streak: int = Field(ge=0)
    best_streak: int = Field(ge=0)
    total_active_days: int = Field(ge=0)
    today_completed: bool
    last_activity: datetime | None
    streak_safe_until: datetime | None


class CalendarResponse(BaseModel):
    """Response returned by GET /api/stats/calendar."""

    data: list[ActivityEntry]


__all__ = [
    "ActivityEntry",
    "ActivityLevel",
    "CalendarResponse",
    "CardRatings",
    "CardStats",
    "ExerciseRatings",
    "ExerciseStats",
    "StatsPeriod",
    "StatsResponse",
    "StreakResponse",
    "StreakSummary",
    "TimeStats",
]
