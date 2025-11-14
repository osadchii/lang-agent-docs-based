"""
Schemas for dialog/chat endpoints exposed to the Mini App.
"""

from __future__ import annotations

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field

from app.models.conversation import MessageRole


class ChatMessage(BaseModel):
    """Single message within the conversation history."""

    id: UUID
    profile_id: UUID
    role: MessageRole
    content: str
    timestamp: datetime

    model_config = ConfigDict(from_attributes=True)


class ChatRequest(BaseModel):
    """Request payload for POST /api/sessions/chat."""

    message: str = Field(
        ...,
        min_length=1,
        max_length=2000,
        description="User message to send to the language tutor LLM.",
    )
    profile_id: UUID | None = Field(
        default=None,
        description="Optional language profile identifier. Defaults to the active profile.",
    )


class ChatResponse(BaseModel):
    """Response body for POST /api/sessions/chat."""

    profile_id: UUID
    message: ChatMessage


class PaginationMeta(BaseModel):
    """Simple offset-based pagination metadata."""

    limit: int
    offset: int
    count: int
    has_more: bool
    next_offset: int | None


class ChatHistoryResponse(BaseModel):
    """Response body for GET /api/dialog/history."""

    messages: list[ChatMessage]
    pagination: PaginationMeta


__all__ = [
    "ChatHistoryResponse",
    "ChatMessage",
    "ChatRequest",
    "ChatResponse",
    "PaginationMeta",
]
