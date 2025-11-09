"""Schemas for language profile endpoints."""

from __future__ import annotations

from datetime import datetime
from typing import List, Optional
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field

from app.models.language_profile import LanguageProfile


class ProfileProgress(BaseModel):
    """Aggregated stats for a profile."""

    cards_count: int = 0
    exercises_count: int = 0
    streak: int = 0


class ProfileResponse(BaseModel):
    """Response payload for a single profile."""

    id: UUID
    user_id: UUID
    language: str
    language_name: str
    current_level: str
    target_level: str
    goals: List[str]
    interface_language: str
    is_active: bool
    progress: ProfileProgress
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


class ProfileListResponse(BaseModel):
    """List wrapper for GET /api/profiles."""

    data: List[ProfileResponse]


class ProfileCreateRequest(BaseModel):
    """Request payload for profile creation."""

    language: str = Field(..., min_length=2, max_length=10)
    current_level: str
    target_level: str
    goals: List[str] = Field(default_factory=list)
    interface_language: str = Field(..., min_length=2, max_length=10)


class ProfileUpdateRequest(BaseModel):
    """Request payload for profile update."""

    current_level: Optional[str] = None
    target_level: Optional[str] = None
    goals: Optional[List[str]] = None
    interface_language: Optional[str] = None


def build_profile_response(profile: LanguageProfile) -> ProfileResponse:
    """Convert domain model to API response."""

    return ProfileResponse(
        id=profile.id,
        user_id=profile.user_id,
        language=profile.language,
        language_name=profile.language_name,
        current_level=profile.current_level,
        target_level=profile.target_level,
        goals=profile.goals,
        interface_language=profile.interface_language,
        is_active=profile.is_active,
        progress=ProfileProgress(
            cards_count=profile.cards_count,
            exercises_count=profile.exercises_count,
            streak=profile.streak,
        ),
        created_at=profile.created_at,
        updated_at=profile.updated_at,
    )
