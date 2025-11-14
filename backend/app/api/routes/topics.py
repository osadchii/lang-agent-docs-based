"""Topic endpoints covering CRUD and LLM suggestions."""

from __future__ import annotations

from typing import Annotated, Any
from uuid import UUID

from fastapi import APIRouter, Depends, Path, Query, Response, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.dependencies import build_enhanced_llm_service, get_cache_client
from app.core.auth import get_current_user
from app.core.cache import CacheClient
from app.core.db import get_session
from app.models.topic import Topic, TopicType
from app.models.user import User
from app.repositories.language_profile import LanguageProfileRepository
from app.repositories.topic import TopicRepository
from app.schemas.topic import (
    TopicCreateRequest,
    TopicDetail,
    TopicListResponse,
    TopicResponse,
    TopicStats,
    TopicSuggestRequest,
    TopicSuggestResponse,
    TopicSummary,
    TopicUpdateRequest,
)
from app.services.topic import TopicService

router = APIRouter(tags=["topics"])


def _build_owner_name(topic: Topic) -> str | None:
    owner: User | None = topic.owner
    if owner is None:
        return None
    for part in (owner.username, owner.first_name, owner.last_name):
        if part:
            return part
    return None


def _topic_payload(topic: Topic) -> dict[str, Any]:
    return {
        "id": topic.id,
        "profile_id": topic.profile_id,
        "name": topic.name,
        "description": topic.description,
        "type": topic.type,
        "is_active": topic.is_active,
        "is_group": topic.is_group,
        "owner_id": topic.owner_id,
        "owner_name": _build_owner_name(topic),
        "exercises_count": topic.exercises_count,
        "accuracy": float(topic.accuracy or 0.0),
        "created_at": topic.created_at,
        "updated_at": topic.updated_at,
    }


def _serialize_topic_summary(topic: Topic) -> TopicSummary:
    return TopicSummary(**_topic_payload(topic))


def _serialize_topic_response(topic: Topic) -> TopicResponse:
    return TopicResponse(**_topic_payload(topic))


def _serialize_detail(topic: Topic) -> TopicDetail:
    summary = _topic_payload(topic)
    stats = TopicStats(
        correct=topic.correct_count,
        partial=topic.partial_count,
        incorrect=topic.incorrect_count,
    )
    return TopicDetail(**summary, stats=stats)


async def get_topic_service(
    session: Annotated[AsyncSession, Depends(get_session)],
    cache: CacheClient = Depends(get_cache_client),  # noqa: B008
) -> TopicService:
    llm_service = build_enhanced_llm_service(cache)
    topic_repo = TopicRepository(session)
    profile_repo = LanguageProfileRepository(session)
    return TopicService(topic_repo, profile_repo, llm_service)


@router.get(
    "/topics",
    response_model=TopicListResponse,
    summary="List topics for the current user",
)
async def list_topics(
    profile_id: Annotated[UUID | None, Query(description="Filter by profile identifier.")] = None,
    topic_type: Annotated[
        TopicType | None,
        Query(description="Filter by topic type (grammar/vocabulary/situation)."),
    ] = None,
    include_group: Annotated[
        bool,
        Query(description="Whether to include shared/group topics in the response."),
    ] = True,
    user: User = Depends(get_current_user),  # noqa: B008
    service: TopicService = Depends(get_topic_service),  # noqa: B008
) -> TopicListResponse:
    topics = await service.list_topics(
        user,
        profile_id=profile_id,
        topic_type=topic_type,
        include_group=include_group,
    )
    data = [_serialize_topic_summary(topic) for topic in topics]
    return TopicListResponse(data=data)


@router.post(
    "/topics",
    response_model=TopicResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create a new topic",
)
async def create_topic(
    payload: TopicCreateRequest,
    user: User = Depends(get_current_user),  # noqa: B008
    service: TopicService = Depends(get_topic_service),  # noqa: B008
) -> TopicResponse:
    topic = await service.create_topic(user, payload)
    await service.session.commit()
    return _serialize_topic_response(topic)


@router.get(
    "/topics/{topic_id}",
    response_model=TopicDetail,
    summary="Fetch a single topic",
)
async def get_topic(
    topic_id: Annotated[UUID, Path(description="Topic identifier")],
    user: User = Depends(get_current_user),  # noqa: B008
    service: TopicService = Depends(get_topic_service),  # noqa: B008
) -> TopicDetail:
    topic = await service.get_topic(user, topic_id)
    return _serialize_detail(topic)


@router.patch(
    "/topics/{topic_id}",
    response_model=TopicResponse,
    summary="Update topic metadata",
)
async def update_topic(
    topic_id: Annotated[UUID, Path(description="Topic identifier")],
    payload: TopicUpdateRequest,
    user: User = Depends(get_current_user),  # noqa: B008
    service: TopicService = Depends(get_topic_service),  # noqa: B008
) -> TopicResponse:
    topic = await service.update_topic(user, topic_id, payload)
    await service.session.commit()
    return _serialize_topic_response(topic)


@router.delete(
    "/topics/{topic_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Delete a topic",
)
async def delete_topic(
    topic_id: Annotated[UUID, Path(description="Topic identifier")],
    user: User = Depends(get_current_user),  # noqa: B008
    service: TopicService = Depends(get_topic_service),  # noqa: B008
) -> Response:
    await service.delete_topic(user, topic_id)
    await service.session.commit()
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.post(
    "/topics/{topic_id}/activate",
    response_model=TopicResponse,
    summary="Mark a topic as active for future exercises",
)
async def activate_topic(
    topic_id: Annotated[UUID, Path(description="Topic identifier")],
    user: User = Depends(get_current_user),  # noqa: B008
    service: TopicService = Depends(get_topic_service),  # noqa: B008
) -> TopicResponse:
    topic = await service.activate_topic(user, topic_id)
    await service.session.commit()
    return _serialize_topic_response(topic)


@router.post(
    "/topics/suggest",
    response_model=TopicSuggestResponse,
    summary="Generate topic suggestions with the LLM",
)
async def suggest_topics(
    payload: TopicSuggestRequest,
    user: User = Depends(get_current_user),  # noqa: B008
    service: TopicService = Depends(get_topic_service),  # noqa: B008
) -> TopicSuggestResponse:
    suggestions = await service.suggest_topics(user, payload)
    return TopicSuggestResponse(suggestions=suggestions.topics)


__all__ = ["get_topic_service", "router"]
