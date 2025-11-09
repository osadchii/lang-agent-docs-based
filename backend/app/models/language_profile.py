"""Domain model for language profiles."""

from __future__ import annotations

from datetime import date, datetime
from typing import List, Optional
from uuid import UUID

from pydantic import BaseModel, ConfigDict

CEFR_LEVELS = ("A1", "A2", "B1", "B2", "C1", "C2")


class LanguageProfile(BaseModel):
    """Language profile entity owned by a user."""

    id: UUID
    user_id: UUID
    language: str
    language_name: str
    current_level: str
    target_level: str
    goals: List[str]
    interface_language: str
    is_active: bool
    streak: int = 0
    best_streak: int = 0
    total_active_days: int = 0
    last_activity_date: Optional[date] = None
    cards_count: int = 0
    exercises_count: int = 0
    deleted: bool = False
    deleted_at: Optional[datetime] = None
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)
