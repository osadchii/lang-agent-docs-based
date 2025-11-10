"""Health check endpoint."""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Final, Literal

from fastapi import APIRouter, status
from pydantic import BaseModel, Field

from app.core.version import APP_VERSION

router = APIRouter()

DEFAULT_CHECKS: Final[dict[str, str]] = {
    "database": "unknown",
    "redis": "unknown",
    "openai": "unknown",
    "stripe": "unknown",
}


class HealthResponse(BaseModel):
    """Schema returned by the /health endpoint."""

    status: Literal["healthy", "unhealthy"]
    timestamp: datetime
    checks: dict[str, str]
    version: str = Field(default=APP_VERSION)


@router.get(
    "/health",
    response_model=HealthResponse,
    status_code=status.HTTP_200_OK,
    summary="Health check",
    tags=["health"],
)
async def health() -> HealthResponse:
    """
    Return the current application health snapshot.

    Placeholders are used for dependency checks until real probes are wired.
    """

    return HealthResponse(
        status="healthy",
        timestamp=datetime.now(tz=timezone.utc),
        checks=DEFAULT_CHECKS.copy(),
        version=APP_VERSION,
    )
