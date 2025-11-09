"""Schemas for user endpoints."""

from __future__ import annotations

from datetime import datetime
from typing import Optional
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, model_validator


class CountLimit(BaseModel):
    """Simple counter limit."""

    used: int = 0
    max: Optional[int] = None


class ResettableLimit(CountLimit):
    """Limits that reset daily."""

    reset_at: Optional[datetime] = None


class UserLimits(BaseModel):
    """Aggregated user limits."""

    profiles: CountLimit
    messages: ResettableLimit
    exercises: ResettableLimit
    cards: CountLimit
    groups: CountLimit


class SubscriptionInfo(BaseModel):
    """Subscription status payload."""

    status: str
    plan: Optional[str] = None
    expires_at: Optional[datetime] = None
    cancel_at_period_end: bool = False


class UserMeResponse(BaseModel):
    """Response for GET /api/users/me."""

    id: UUID
    telegram_id: int
    first_name: Optional[str] = None
    last_name: Optional[str] = None
    username: Optional[str] = None
    is_premium: bool
    trial_ends_at: Optional[datetime] = None
    premium_expires_at: Optional[datetime] = None
    created_at: datetime
    updated_at: datetime
    subscription: SubscriptionInfo
    limits: UserLimits

    model_config = ConfigDict(from_attributes=True)


class UserUpdateRequest(BaseModel):
    """Request payload for PATCH /api/users/me."""

    first_name: Optional[str] = Field(default=None, max_length=255)
    last_name: Optional[str] = Field(default=None, max_length=255)

    @model_validator(mode="after")
    def validate_fields(self) -> "UserUpdateRequest":
        if self.first_name is None and self.last_name is None:
            raise ValueError("Нужно передать хотя бы одно поле для обновления.")
        return self
