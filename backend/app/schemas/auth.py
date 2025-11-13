"""
Pydantic schemas for authentication endpoints.
"""

from __future__ import annotations

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field


class ValidateInitDataRequest(BaseModel):
    """Request schema for POST /api/auth/validate."""

    init_data: str = Field(
        ...,
        description="initData string from Telegram WebApp.initData",
        min_length=1,
    )

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "init_data": (
                    "query_id=xxx&user=%7B%22id%22%3A123...%7D"
                    "&auth_date=1234567890&hash=abc123..."
                )
            }
        }
    )


class UserResponse(BaseModel):
    """User information in auth response."""

    id: UUID
    telegram_id: int
    first_name: str
    last_name: str | None
    username: str | None
    is_premium: bool
    trial_ends_at: datetime | None
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class ValidateInitDataResponse(BaseModel):
    """Response schema for POST /api/auth/validate."""

    user: UserResponse
    token: str = Field(..., description="JWT access token")
    expires_at: datetime = Field(..., description="Token expiration time (UTC)")

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "user": {
                    "id": "123e4567-e89b-12d3-a456-426614174000",
                    "telegram_id": 123456789,
                    "first_name": "John",
                    "last_name": "Doe",
                    "username": "johndoe",
                    "is_premium": False,
                    "trial_ends_at": "2025-01-15T00:00:00Z",
                    "created_at": "2025-01-08T12:00:00Z",
                },
                "token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
                "expires_at": "2025-01-09T12:00:00Z",
            }
        }
    )
