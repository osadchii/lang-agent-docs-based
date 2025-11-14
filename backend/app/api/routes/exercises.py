"""Exercise generation, submission, and history endpoints."""

from __future__ import annotations

from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, Path, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.dependencies import build_enhanced_llm_service, get_cache_client
from app.core.auth import get_current_user
from app.core.cache import CacheClient
from app.core.db import get_session
from app.models.exercise import ExerciseHistory
from app.models.user import User
from app.repositories.exercise import ExerciseHistoryRepository
from app.repositories.language_profile import LanguageProfileRepository
from app.repositories.topic import TopicRepository
from app.schemas.dialog import PaginationMeta
from app.schemas.exercise import (
    ExerciseGenerateRequest,
    ExerciseHintResponse,
    ExerciseHistoryEntry,
    ExerciseHistoryResponse,
    ExerciseSubmissionResponse,
    ExerciseSubmitRequest,
    GeneratedExerciseResponse,
)
from app.services.exercise import ExerciseService

router = APIRouter(tags=["exercises"])


async def get_exercise_service(
    session: Annotated[AsyncSession, Depends(get_session)],
    cache: CacheClient = Depends(get_cache_client),  # noqa: B008
) -> ExerciseService:
    llm_service = build_enhanced_llm_service(cache)
    history_repo = ExerciseHistoryRepository(session)
    topic_repo = TopicRepository(session)
    profile_repo = LanguageProfileRepository(session)
    return ExerciseService(history_repo, topic_repo, profile_repo, llm_service, cache)


def _serialize_history_entry(entry: ExerciseHistory) -> ExerciseHistoryEntry:
    topic_name = entry.topic.name if entry.topic else "????????"
    return ExerciseHistoryEntry(
        id=entry.id,
        topic_id=entry.topic_id,
        topic_name=topic_name,
        type=entry.type,
        question=entry.question,
        prompt=entry.prompt,
        user_answer=entry.user_answer,
        result=entry.result,
        used_hint=entry.used_hint,
        duration_seconds=entry.duration_seconds,
        completed_at=entry.completed_at,
    )


@router.post(
    "/exercises/generate",
    response_model=GeneratedExerciseResponse,
    status_code=status.HTTP_200_OK,
    summary="Generate an exercise for the current topic",
)
async def generate_exercise(
    payload: ExerciseGenerateRequest,
    user: User = Depends(get_current_user),  # noqa: B008
    service: ExerciseService = Depends(get_exercise_service),  # noqa: B008
) -> GeneratedExerciseResponse:
    return await service.generate_exercise(user, payload)


@router.post(
    "/exercises/{exercise_id}/submit",
    response_model=ExerciseSubmissionResponse,
    summary="Submit an answer for an exercise",
)
async def submit_exercise(
    exercise_id: Annotated[UUID, Path(description="Exercise identifier")],
    payload: ExerciseSubmitRequest,
    user: User = Depends(get_current_user),  # noqa: B008
    service: ExerciseService = Depends(get_exercise_service),  # noqa: B008
) -> ExerciseSubmissionResponse:
    result = await service.submit_answer(user, exercise_id, payload)
    await service.session.commit()
    return result


@router.post(
    "/exercises/{exercise_id}/hint",
    response_model=ExerciseHintResponse,
    summary="Retrieve a hint for the pending exercise",
)
async def get_hint(
    exercise_id: Annotated[UUID, Path(description="Exercise identifier")],
    user: User = Depends(get_current_user),  # noqa: B008
    service: ExerciseService = Depends(get_exercise_service),  # noqa: B008
) -> ExerciseHintResponse:
    hint = await service.get_hint(user, exercise_id)
    return ExerciseHintResponse(hint=hint)


@router.get(
    "/exercises/history",
    response_model=ExerciseHistoryResponse,
    summary="Return exercise history for the current user",
)
async def list_history(
    topic_id: Annotated[UUID | None, Query(description="Filter by topic identifier.")] = None,
    profile_id: Annotated[UUID | None, Query(description="Filter by profile identifier.")] = None,
    limit: Annotated[
        int,
        Query(ge=1, le=100, description="Maximum history entries to return."),
    ] = 20,
    offset: Annotated[
        int,
        Query(ge=0, description="Number of entries to skip."),
    ] = 0,
    user: User = Depends(get_current_user),  # noqa: B008
    service: ExerciseService = Depends(get_exercise_service),  # noqa: B008
) -> ExerciseHistoryResponse:
    entries, total = await service.list_history(
        user,
        profile_id=profile_id,
        topic_id=topic_id,
        limit=limit,
        offset=offset,
    )
    data = [_serialize_history_entry(entry) for entry in entries]
    has_more = offset + limit < total
    pagination = PaginationMeta(
        limit=limit,
        offset=offset,
        count=total,
        has_more=has_more,
        next_offset=(offset + limit) if has_more else None,
    )
    return ExerciseHistoryResponse(data=data, pagination=pagination)


__all__ = ["get_exercise_service", "router"]
