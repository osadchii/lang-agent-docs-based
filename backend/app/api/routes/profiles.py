"""REST endpoints for managing language profiles."""

from __future__ import annotations

from typing import Annotated, cast
from uuid import UUID

from fastapi import APIRouter, Depends, Response, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.auth import get_current_user
from app.core.db import get_session
from app.models.language_profile import LanguageProfile
from app.models.user import User
from app.repositories.language_profile import LanguageProfileRepository
from app.schemas.profile import (
    CEFRLevel,
    LanguageProfileCreate,
    LanguageProfileListResponse,
    LanguageProfileProgress,
    LanguageProfileResponse,
    LanguageProfileUpdate,
)
from app.services.language_profile import LanguageProfileService

router = APIRouter(tags=["profiles"])


def _serialize_profile(profile: LanguageProfile) -> LanguageProfileResponse:
    """Convert ORM model to API schema."""
    current_level = cast(CEFRLevel, profile.current_level)
    target_level = cast(CEFRLevel, profile.target_level)
    progress = LanguageProfileProgress(
        cards_count=0,
        exercises_count=0,
        streak=profile.streak,
    )
    return LanguageProfileResponse(
        id=profile.id,
        user_id=profile.user_id,
        language=profile.language,
        language_name=profile.language_name,
        current_level=current_level,
        target_level=target_level,
        goals=list(profile.goals),
        interface_language=profile.interface_language,
        is_active=profile.is_active,
        progress=progress,
        created_at=profile.created_at,
        updated_at=profile.updated_at,
    )


async def get_language_profile_service(
    session: Annotated[AsyncSession, Depends(get_session)],
) -> LanguageProfileService:
    repository = LanguageProfileRepository(session)
    return LanguageProfileService(repository)


@router.get(
    "/profiles",
    response_model=LanguageProfileListResponse,
    summary="List language profiles for the current user",
)
async def list_profiles(
    user: User = Depends(get_current_user),  # noqa: B008
    service: LanguageProfileService = Depends(get_language_profile_service),  # noqa: B008
) -> LanguageProfileListResponse:
    profiles = await service.list_profiles(user)
    data = [_serialize_profile(profile) for profile in profiles]
    return LanguageProfileListResponse(data=data)


@router.post(
    "/profiles",
    response_model=LanguageProfileResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create a new language profile",
)
async def create_profile(
    payload: LanguageProfileCreate,
    user: User = Depends(get_current_user),  # noqa: B008
    service: LanguageProfileService = Depends(get_language_profile_service),  # noqa: B008
) -> LanguageProfileResponse:
    profile = await service.create_profile(user, payload)
    await service.session.commit()
    return _serialize_profile(profile)


@router.get(
    "/profiles/{profile_id}",
    response_model=LanguageProfileResponse,
    summary="Fetch a single profile",
)
async def get_profile(
    profile_id: UUID,
    user: User = Depends(get_current_user),  # noqa: B008
    service: LanguageProfileService = Depends(get_language_profile_service),  # noqa: B008
) -> LanguageProfileResponse:
    profile = await service.get_profile(user, profile_id)
    return _serialize_profile(profile)


@router.patch(
    "/profiles/{profile_id}",
    response_model=LanguageProfileResponse,
    summary="Update profile settings",
)
async def update_profile(
    profile_id: UUID,
    payload: LanguageProfileUpdate,
    user: User = Depends(get_current_user),  # noqa: B008
    service: LanguageProfileService = Depends(get_language_profile_service),  # noqa: B008
) -> LanguageProfileResponse:
    profile = await service.update_profile(user, profile_id, payload)
    await service.session.commit()
    return _serialize_profile(profile)


@router.delete(
    "/profiles/{profile_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Soft delete a profile",
)
async def delete_profile(
    profile_id: UUID,
    user: User = Depends(get_current_user),  # noqa: B008
    service: LanguageProfileService = Depends(get_language_profile_service),  # noqa: B008
) -> Response:
    await service.delete_profile(user, profile_id)
    await service.session.commit()
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.post(
    "/profiles/{profile_id}/activate",
    response_model=LanguageProfileResponse,
    summary="Activate a profile for future sessions",
)
async def activate_profile(
    profile_id: UUID,
    user: User = Depends(get_current_user),  # noqa: B008
    service: LanguageProfileService = Depends(get_language_profile_service),  # noqa: B008
) -> LanguageProfileResponse:
    profile = await service.activate_profile(user, profile_id)
    await service.session.commit()
    return _serialize_profile(profile)


__all__ = ["get_language_profile_service", "router"]
