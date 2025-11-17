"""Dialog endpoints for the Mini App chat experience."""

from __future__ import annotations

import logging
import uuid
from datetime import datetime, timezone
from types import SimpleNamespace
from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, Query, Response, status
from openai import OpenAIError
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.auth import get_current_user
from app.core.config import settings
from app.core.db import get_session
from app.core.errors import ApplicationError, ErrorCode, ExternalServiceError, NotFoundError
from app.models.conversation import MessageRole
from app.models.language_profile import LanguageProfile
from app.models.user import User
from app.repositories.conversation import ConversationRepository
from app.schemas.dialog import (
    ChatHistoryResponse,
    ChatMessage,
    ChatRequest,
    ChatResponse,
    PaginationMeta,
)
from app.services import DialogService, LLMService
from app.services.rate_limit import RateLimitedAction, rate_limit_service

logger = logging.getLogger("app.api.dialog")

router = APIRouter(tags=["dialog"])

MAX_PAGE_SIZE = 50
MAX_HISTORY_WINDOW = 200
PROFILE_ID_FIELD = Query(
    description="Optional profile identifier. Defaults to the active profile.",
)
LIMIT_FIELD = Query(
    ge=1,
    le=MAX_PAGE_SIZE,
    description="Maximum number of messages to return.",
)
OFFSET_FIELD = Query(
    ge=0,
    le=MAX_HISTORY_WINDOW,
    description="Number of most recent messages to skip.",
)


async def get_dialog_service(
    session: Annotated[AsyncSession, Depends(get_session)],
) -> DialogService:
    """Instantiate DialogService with configured dependencies."""
    llm_service = LLMService(
        api_key=settings.openai_api_key.get_secret_value(),
        model=settings.llm_model,
        temperature=settings.llm_temperature,
    )
    conversation_repo = ConversationRepository(session)
    return DialogService(llm_service, conversation_repo)


async def _resolve_profile(
    dialog_service: DialogService,
    user: User,
    requested_profile_id: UUID | None,
) -> LanguageProfile:
    session = dialog_service.conversation_repo.session

    if requested_profile_id is None:
        return await dialog_service.get_or_create_default_profile(user, session)

    stmt = select(LanguageProfile).where(
        LanguageProfile.id == requested_profile_id,
        LanguageProfile.user_id == user.id,
        LanguageProfile.deleted == False,  # noqa: E712
    )
    result = await session.execute(stmt)
    profile = result.scalar_one_or_none()

    if profile is None:
        raise NotFoundError(
            code=ErrorCode.PROFILE_NOT_FOUND,
            message="Requested profile was not found for the current user.",
        )

    return profile


async def _build_assistant_message(
    dialog_service: DialogService,
    *,
    user: User,
    profile_id: UUID,
    fallback_text: str,
) -> ChatMessage:
    """Fetch the latest assistant message or synthesize fallback data."""
    recent = await dialog_service.conversation_repo.get_recent_for_profile(
        user_id=user.id,
        profile_id=profile_id,
        limit=4,
    )

    assistant_entry: object | None = next(
        (msg for msg in recent if getattr(msg, "role", None) == MessageRole.ASSISTANT),
        None,
    )

    if assistant_entry is None:
        assistant_entry = SimpleNamespace(
            id=uuid.uuid4(),
            profile_id=profile_id,
            role=MessageRole.ASSISTANT,
            content=fallback_text,
            timestamp=datetime.now(tz=timezone.utc),
        )

    return ChatMessage.model_validate(assistant_entry)


@router.post(
    "/sessions/chat",
    response_model=ChatResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Send a user question to the language tutor LLM",
)
async def chat_with_tutor(
    request: ChatRequest,
    response: Response,
    user: User = Depends(get_current_user),  # noqa: B008
    dialog_service: DialogService = Depends(get_dialog_service),  # noqa: B008
) -> ChatResponse:
    """Send a message to DialogService and return the assistant response."""
    rate_limit_state = await rate_limit_service.enforce_action_limit(
        user,
        RateLimitedAction.LLM_MESSAGES,
    )

    profile = await _resolve_profile(dialog_service, user, request.profile_id)

    try:
        reply = await dialog_service.process_message(
            user=user,
            profile_id=profile.id,
            message=request.message,
        )
    except OpenAIError as exc:  # pragma: no cover - exercised via tests with override
        logger.exception("LLM request failed")
        raise ExternalServiceError(
            code=ErrorCode.LLM_SERVICE_ERROR,
            message="Language model is currently unavailable. Please try again later.",
            status_code=status.HTTP_502_BAD_GATEWAY,
            details={"reason": str(exc)},
        ) from exc

    message = await _build_assistant_message(
        dialog_service,
        user=user,
        profile_id=profile.id,
        fallback_text=reply,
    )
    result = ChatResponse(profile_id=profile.id, message=message)
    if rate_limit_state:
        rate_limit_state.apply(response)
    return result


@router.get(
    "/dialog/history",
    response_model=ChatHistoryResponse,
    summary="Fetch the latest dialog history for the current user",
)
async def get_dialog_history(
    profile_id: Annotated[UUID | None, PROFILE_ID_FIELD] = None,
    limit: Annotated[int, LIMIT_FIELD] = 20,
    offset: Annotated[int, OFFSET_FIELD] = 0,
    user: User = Depends(get_current_user),  # noqa: B008
    dialog_service: DialogService = Depends(get_dialog_service),  # noqa: B008
) -> ChatHistoryResponse:
    """Return a chronologically ordered slice of chat history."""
    if limit + offset > MAX_HISTORY_WINDOW:
        raise ApplicationError(
            code=ErrorCode.INVALID_FIELD_VALUE,
            message="Requested window is too large. Use smaller limit/offset.",
            status_code=status.HTTP_400_BAD_REQUEST,
            details={"max_window": MAX_HISTORY_WINDOW},
        )

    profile = await _resolve_profile(dialog_service, user, profile_id)

    fetch_limit = limit + offset + 1
    history = await dialog_service.conversation_repo.get_recent_for_profile(
        user_id=user.id,
        profile_id=profile.id,
        limit=fetch_limit,
    )

    slice_end = offset + limit
    subset = history[offset:slice_end]
    count = len(subset)
    has_more = len(history) > slice_end

    messages = [ChatMessage.model_validate(msg) for msg in reversed(subset)]

    pagination = PaginationMeta(
        limit=limit,
        offset=offset,
        count=count,
        has_more=has_more,
        next_offset=slice_end if has_more else None,
    )

    return ChatHistoryResponse(messages=messages, pagination=pagination)


__all__ = ["get_dialog_service", "router"]
