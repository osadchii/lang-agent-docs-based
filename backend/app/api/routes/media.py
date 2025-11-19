"""Media endpoints powering OCR features."""

from __future__ import annotations

import logging
from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, File, Form, UploadFile, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.dependencies import build_enhanced_llm_service, build_ocr_service, get_cache_client
from app.core.auth import get_current_user
from app.core.cache import CacheClient
from app.core.db import get_session
from app.core.errors import ApplicationError, ErrorCode
from app.models.language_profile import LanguageProfile
from app.models.user import User
from app.repositories.card import CardRepository
from app.repositories.language_profile import LanguageProfileRepository
from app.schemas.media import OCRAnalyzeResponse, OCRSegmentPayload
from app.services.media import ImageInput, OCRAnalysis, OCRService

router = APIRouter(tags=["media"])
logger = logging.getLogger("app.api.media")


async def _resolve_profile(
    repo: LanguageProfileRepository,
    user: User,
    requested_profile_id: UUID | None,
) -> LanguageProfile:
    if requested_profile_id is not None:
        profile = await repo.get_by_id_for_user(requested_profile_id, user.id)
        if profile is None:
            raise ApplicationError(
                code=ErrorCode.PROFILE_NOT_FOUND,
                message="Профиль не найден или принадлежит другому пользователю.",
            )
        return profile

    profile = await repo.get_active_for_user(user.id)
    if profile is None:
        raise ApplicationError(
            code=ErrorCode.PROFILE_NOT_FOUND,
            message="Нужен хотя бы один активный профиль, чтобы распознавать текст.",
        )
    return profile


def _map_segments(analysis: OCRAnalysis) -> list[OCRSegmentPayload]:
    return [
        OCRSegmentPayload(
            image_index=segment.index,
            detected_languages=segment.detected_languages,
            contains_target_language=segment.contains_target_language,
            confidence=segment.confidence,
            full_text=segment.full_text,
            target_text=segment.target_text,
        )
        for segment in sorted(analysis.segments, key=lambda item: item.index)
    ]


async def _to_image_inputs(files: list[UploadFile]) -> list[ImageInput]:
    inputs: list[ImageInput] = []
    for idx, file in enumerate(files, start=1):
        data = await file.read()
        await file.close()
        inputs.append(
            ImageInput(
                name=file.filename or f"image-{idx}",
                content_type=file.content_type,
                data=data,
            )
        )
    return inputs


@router.post(
    "/media/ocr",
    response_model=OCRAnalyzeResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Extract text from uploaded images and suggest flashcards",
)
async def analyze_images(
    images: Annotated[
        list[UploadFile],
        File(description="1-3 images (JPG/PNG/WEBP/HEIC) sized up to 10 MB each."),
    ],
    session: Annotated[AsyncSession, Depends(get_session)],
    cache: CacheClient = Depends(get_cache_client),  # noqa: B008
    ocr_service: OCRService = Depends(build_ocr_service),  # noqa: B008
    profile_id: Annotated[
        UUID | None,
        Form(
            description="Optional profile identifier. "
            "Если не указан, используется активный профиль.",
        ),
    ] = None,
    user: User = Depends(get_current_user),  # noqa: B008
) -> OCRAnalyzeResponse:
    """Run OCR for uploaded images and return recognized text plus card suggestions."""
    if not images:
        raise ApplicationError(
            code=ErrorCode.INVALID_FIELD_VALUE,
            message="Нужно прикрепить хотя бы одно изображение.",
        )

    image_inputs = await _to_image_inputs(images)

    profile_repo = LanguageProfileRepository(session)
    profile = await _resolve_profile(profile_repo, user, profile_id)

    analysis = await ocr_service.analyze(
        image_inputs,
        target_language_code=profile.language,
        target_language_name=profile.language_name,
    )

    card_repo = CardRepository(session)
    llm_service = build_enhanced_llm_service(cache)
    existing_lemmas = await card_repo.list_lemmas_for_profile(profile.id)

    suggestions_list = []
    if analysis.combined_text:
        suggestions, usage = await llm_service.suggest_words_from_text(
            text=analysis.combined_text,
            language=profile.language,
            interface_language=profile.interface_language,
            level=profile.current_level,
            goals=list(profile.goals),
            known_lemmas=existing_lemmas,
        )
        suggestions_list = suggestions.suggestions
        await llm_service.track_token_usage(
            db_session=session,
            user_id=str(user.id),
            profile_id=str(profile.id),
            usage=usage,
            operation="ocr_word_suggestions",
        )

    detected_languages = sorted(
        {lang for segment in analysis.segments for lang in segment.detected_languages}
    )

    logger.info(
        "OCR request processed",
        extra={
            "user_id": str(user.id),
            "profile_id": str(profile.id),
            "images": len(images),
            "has_target_language": analysis.has_target_language,
        },
    )

    return OCRAnalyzeResponse(
        profile_id=profile.id,
        target_language=profile.language,
        target_language_name=profile.language_name,
        combined_text=analysis.combined_text,
        has_target_language=analysis.has_target_language,
        detected_languages=detected_languages,
        segments=_map_segments(analysis),
        suggestions=suggestions_list,
    )


__all__ = ["router"]
