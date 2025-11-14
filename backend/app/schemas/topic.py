"""Pydantic schemas powering /api/topics endpoints."""

from __future__ import annotations

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, model_validator

from app.models.topic import TopicType
from app.schemas.llm_responses import TopicSuggestion


class TopicBase(BaseModel):
    """Shared representation between summary/detail responses."""

    id: UUID
    profile_id: UUID
    name: str
    description: str | None
    type: TopicType
    is_active: bool
    is_group: bool
    owner_id: UUID | None
    owner_name: str | None
    exercises_count: int
    accuracy: float
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


class TopicSummary(TopicBase):
    """Response entry for GET /api/topics."""

    pass


class TopicStats(BaseModel):
    """Aggregated stats block used in detail response."""

    correct: int
    partial: int
    incorrect: int


class TopicDetail(TopicBase):
    """Detailed topic payload with stats."""

    stats: TopicStats


class TopicListResponse(BaseModel):
    """Wrapper for GET /api/topics list response."""

    data: list[TopicSummary]


class TopicResponse(TopicSummary):
    """Re-use summary payload for create/update responses."""

    pass


class TopicCreateRequest(BaseModel):
    """Request body for POST /api/topics."""

    profile_id: UUID
    name: str = Field(min_length=3, max_length=200)
    description: str | None = Field(default=None, max_length=1000)
    type: TopicType


class TopicUpdateRequest(BaseModel):
    """Request body for PATCH /api/topics/{topic_id}."""

    name: str | None = Field(default=None, min_length=3, max_length=200)
    description: str | None = Field(default=None, max_length=1000)

    @model_validator(mode="after")
    def _ensure_non_empty(self) -> "TopicUpdateRequest":
        if self.name is None and self.description is None:
            raise ValueError("?????????? ??????? ???? ??????? ??? ??????????.")
        return self


class TopicSuggestRequest(BaseModel):
    """Request body for POST /api/topics/suggest."""

    profile_id: UUID


class TopicSuggestResponse(BaseModel):
    """Response body containing LLM suggestions."""

    suggestions: list[TopicSuggestion]


__all__ = [
    "TopicCreateRequest",
    "TopicDetail",
    "TopicListResponse",
    "TopicResponse",
    "TopicSuggestRequest",
    "TopicSuggestResponse",
    "TopicSummary",
    "TopicUpdateRequest",
]
