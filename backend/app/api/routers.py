"""
API routers for the application.

This module defines all API route handlers according to docs/backend-api.md.
"""

from datetime import datetime
from typing import Any, Dict
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status

from app.core.config import settings
from app.exceptions.domain_error import DomainError
from app.exceptions.telegram_init_data_error import TelegramInitDataError
from app.api.dependencies.auth import get_current_user
from app.models.user import User
from app.schemas.profile import (
    ProfileCreateRequest,
    ProfileListResponse,
    ProfileResponse,
    ProfileUpdateRequest,
    build_profile_response,
)
from app.schemas.auth_request import InitDataRequest
from app.schemas.auth_response import AuthResponse
from app.services.auth_service import AuthService, get_auth_service
from app.schemas.user import UserMeResponse, UserUpdateRequest
from app.services.profile_service import ProfileService, get_profile_service
from app.services.user_service import UserService, get_user_service

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


@router.get(
    "/users/me",
    response_model=UserMeResponse,
    status_code=status.HTTP_200_OK,
)
async def get_current_user_info(
    user: User = Depends(get_current_user),
    user_service: UserService = Depends(get_user_service),
) -> UserMeResponse:
    """Return current user info with limits."""

    return user_service.get_user_overview(user)


@router.patch(
    "/users/me",
    response_model=UserMeResponse,
    status_code=status.HTTP_200_OK,
)
async def update_current_user(
    payload: UserUpdateRequest,
    user: User = Depends(get_current_user),
    user_service: UserService = Depends(get_user_service),
) -> UserMeResponse:
    """Update mutable user fields."""

    try:
        updated_user = user_service.update_user(
            user=user,
            first_name=payload.first_name,
            last_name=payload.last_name,
        )
        return user_service.get_user_overview(updated_user)
    except DomainError as exc:  # pragma: no cover - marshalled to HTTP exception
        raise _domain_error_to_http(exc) from exc


@router.get(
    "/profiles",
    response_model=ProfileListResponse,
    status_code=status.HTTP_200_OK,
)
async def list_profiles(
    user: User = Depends(get_current_user),
    profile_service: ProfileService = Depends(get_profile_service),
) -> ProfileListResponse:
    """Return all language profiles for the current user."""

    profiles = profile_service.list_profiles(user)
    data = [build_profile_response(profile) for profile in profiles]
    return ProfileListResponse(data=data)


@router.post(
    "/profiles",
    response_model=ProfileResponse,
    status_code=status.HTTP_201_CREATED,
)
async def create_profile(
    payload: ProfileCreateRequest,
    user: User = Depends(get_current_user),
    profile_service: ProfileService = Depends(get_profile_service),
) -> ProfileResponse:
    """Create a new language profile."""

    try:
        profile = profile_service.create_profile(
            user=user,
            language=payload.language,
            current_level=payload.current_level,
            target_level=payload.target_level,
            goals=payload.goals,
            interface_language=payload.interface_language,
        )
    except DomainError as exc:  # pragma: no cover
        raise _domain_error_to_http(exc) from exc
    return build_profile_response(profile)


@router.get(
    "/profiles/{profile_id}",
    response_model=ProfileResponse,
    status_code=status.HTTP_200_OK,
)
async def get_profile(
    profile_id: UUID,
    user: User = Depends(get_current_user),
    profile_service: ProfileService = Depends(get_profile_service),
) -> ProfileResponse:
    """Return a single profile."""

    try:
        profile = profile_service.get_profile(user, profile_id)
    except DomainError as exc:  # pragma: no cover
        raise _domain_error_to_http(exc) from exc
    return build_profile_response(profile)


@router.patch(
    "/profiles/{profile_id}",
    response_model=ProfileResponse,
    status_code=status.HTTP_200_OK,
)
async def update_profile(
    profile_id: UUID,
    payload: ProfileUpdateRequest,
    user: User = Depends(get_current_user),
    profile_service: ProfileService = Depends(get_profile_service),
) -> ProfileResponse:
    """Update profile fields."""

    try:
        profile = profile_service.update_profile(
            user=user,
            profile_id=profile_id,
            current_level=payload.current_level,
            target_level=payload.target_level,
            goals=payload.goals,
            interface_language=payload.interface_language,
        )
    except DomainError as exc:  # pragma: no cover
        raise _domain_error_to_http(exc) from exc
    return build_profile_response(profile)


@router.delete(
    "/profiles/{profile_id}",
    status_code=status.HTTP_204_NO_CONTENT,
)
async def delete_profile(
    profile_id: UUID,
    user: User = Depends(get_current_user),
    profile_service: ProfileService = Depends(get_profile_service),
) -> None:
    """Delete a profile (soft delete)."""

    try:
        profile_service.delete_profile(user, profile_id)
    except DomainError as exc:  # pragma: no cover
        raise _domain_error_to_http(exc) from exc


@router.post(
    "/profiles/{profile_id}/activate",
    response_model=ProfileResponse,
    status_code=status.HTTP_200_OK,
)
async def activate_profile(
    profile_id: UUID,
    user: User = Depends(get_current_user),
    profile_service: ProfileService = Depends(get_profile_service),
) -> ProfileResponse:
    """Make the selected profile active."""

    try:
        profile = profile_service.activate_profile(user, profile_id)
    except DomainError as exc:  # pragma: no cover
        raise _domain_error_to_http(exc) from exc
    return build_profile_response(profile)


def _domain_error_to_http(error: DomainError) -> HTTPException:
    """Convert DomainError to HTTPException with uniform detail."""

    return HTTPException(
        status_code=error.status_code,
        detail={
            "code": error.error_code,
            "message": str(error),
            "details": error.details,
        },
    )
