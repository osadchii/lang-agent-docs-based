"""Request models for authentication endpoints."""

from pydantic import BaseModel, Field


class InitDataRequest(BaseModel):
    """Request body for POST /api/auth/validate."""

    init_data: str = Field(..., min_length=1, description="Telegram WebApp initData string")
