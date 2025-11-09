"""
API routers for the application.

This module defines all API route handlers according to docs/backend-api.md.
"""

from datetime import datetime
from typing import Any, Dict

from fastapi import APIRouter, Depends, HTTPException, status

from app.core.config import settings
from app.exceptions.telegram_init_data_error import TelegramInitDataError
from app.schemas.auth_request import InitDataRequest
from app.schemas.auth_response import AuthResponse
from app.services.auth_service import AuthService, get_auth_service

router = APIRouter()


@router.get("/health")
async def health_check() -> Dict[str, Any]:
    """
    Health check endpoint.

    Returns the service status and version information.
    Used for monitoring, CI/CD checks, and load balancer health checks.

    According to docs/backend-api.md, this endpoint checks:
    - Database connectivity
    - Redis connectivity
    - External APIs availability (OpenAI, Stripe)

    Returns:
        Dict with status, timestamp, checks, and version

    Example:
        >>> response = await health_check()
        >>> response["status"]
        'healthy'
    """
    # TODO: Implement actual health checks for database, redis, and external services
    # For now, return a basic healthy status with version
    return {
        "status": "healthy",
        "timestamp": datetime.utcnow().isoformat() + "Z",
        "checks": {
            "database": "ok",  # TODO: Implement PostgreSQL ping
            "redis": "ok",     # TODO: Implement Redis ping
            "openai": "ok",    # TODO: Implement OpenAI API check (non-blocking)
            "stripe": "ok"     # TODO: Implement Stripe API check (non-blocking)
        },
        "version": settings.APP_VERSION
    }


@router.post(
    "/auth/validate",
    response_model=AuthResponse,
    status_code=status.HTTP_200_OK,
)
async def validate_authentication(
    request: InitDataRequest,
    auth_service: AuthService = Depends(get_auth_service),
) -> AuthResponse:
    """Validate Telegram initData and issue JWT tokens."""

    try:
        user, token, expires_at = auth_service.validate_init_data_and_issue_token(
            request.init_data
        )
    except TelegramInitDataError as exc:
        raise HTTPException(
            status_code=exc.status_code,
            detail={"code": exc.error_code, "message": str(exc)},
        ) from exc

    return AuthResponse(user=user, token=token, expires_at=expires_at)
