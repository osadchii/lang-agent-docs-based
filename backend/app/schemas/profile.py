"""Pydantic schemas for language profile endpoints."""

from __future__ import annotations

from datetime import datetime
from typing import Literal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator


class LanguageProfileProgress(BaseModel):
    """Aggregated counters associated with a profile."""

    cards_count: int = 0
    exercises_count: int = 0
    streak: int = 0


CEFRLevel = Literal["A1", "A2", "B1", "B2", "C1", "C2"]


class LanguageProfileBase(BaseModel):
    """Fields shared between profile responses."""

    id: UUID
    user_id: UUID
    language: str
    language_name: str
    current_level: CEFRLevel
    target_level: CEFRLevel
    goals: list[str]
    interface_language: str
    is_active: bool
    progress: LanguageProfileProgress
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


class LanguageProfileCreate(BaseModel):
    """Request body for POST /api/profiles."""

    language: str = Field(..., min_length=2, max_length=10)
    current_level: CEFRLevel
    target_level: CEFRLevel
    goals: list[str] = Field(default_factory=list, min_length=1, max_length=8)
    interface_language: str = Field(default="ru", min_length=2, max_length=10)

    model_config = ConfigDict(extra="forbid")

    @field_validator("language")
    @classmethod
    def _normalize_language(cls, value: str) -> str:
        return value.lower()

    @field_validator("goals")
    @classmethod
    def _strip_goals(cls, goals: list[str]) -> list[str]:
        return [goal.strip() for goal in goals if goal.strip()]


class LanguageProfileUpdate(BaseModel):
    """Request body for PATCH /api/profiles/{profile_id}."""

    current_level: CEFRLevel | None = None
    target_level: CEFRLevel | None = None
    goals: list[str] | None = None
    interface_language: str | None = Field(default=None, min_length=2, max_length=10)

    model_config = ConfigDict(extra="forbid")

    @field_validator("goals")
    @classmethod
    def _strip_optional_goals(cls, goals: list[str] | None) -> list[str] | None:
        if goals is None:
            return None
        cleaned = [goal.strip() for goal in goals if goal.strip()]
        return cleaned or None

    @model_validator(mode="after")
    def _ensure_payload_not_empty(self) -> "LanguageProfileUpdate":
        if not any(
            (
                self.current_level,
                self.target_level,
                self.goals is not None,
                self.interface_language is not None,
            )
        ):
            raise ValueError("Необходимо передать хотя бы одно поле для обновления.")
        return self


class LanguageProfileResponse(LanguageProfileBase):
    """Single profile representation."""

    pass


class LanguageProfileListResponse(BaseModel):
    """Response wrapper for GET /api/profiles."""

    data: list[LanguageProfileResponse]


__all__ = [
    "CEFRLevel",
    "LanguageProfileBase",
    "LanguageProfileCreate",
    "LanguageProfileListResponse",
    "LanguageProfileProgress",
    "LanguageProfileResponse",
    "LanguageProfileUpdate",
]
