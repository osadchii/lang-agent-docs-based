"""Response models for authentication endpoints."""

from datetime import datetime

from pydantic import BaseModel, ConfigDict

from app.models.user import User


class AuthResponse(BaseModel):
    """Response payload for POST /api/auth/validate."""

    user: User
    token: str
    expires_at: datetime

    model_config = ConfigDict(from_attributes=True)
