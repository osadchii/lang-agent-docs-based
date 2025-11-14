"""Schemas describing exercise generation and history payloads."""

from __future__ import annotations

from datetime import datetime
from typing import Any
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field

from app.models.exercise import ExerciseResultType, ExerciseType
from app.schemas.dialog import PaginationMeta
from app.schemas.llm_responses import Mistake


class ExerciseGenerateRequest(BaseModel):
    """Request body for POST /api/exercises/generate."""

    topic_id: UUID
    type: ExerciseType = Field(default=ExerciseType.FREE_TEXT)


class PendingExercise(BaseModel):
    """Internal representation cached between generate/submit steps."""

    id: UUID
    user_id: UUID
    profile_id: UUID
    topic_id: UUID
    type: ExerciseType
    question: str
    prompt: str
    correct_answer: str
    hint: str | None = None
    explanation: str | None = None
    alternatives: list[str] = Field(default_factory=list)
    options: list[str] | None = None
    correct_index: int | None = None
    metadata: dict[str, Any] = Field(default_factory=dict)


class GeneratedExerciseResponse(BaseModel):
    """Response payload returned to the Mini App."""

    id: UUID
    topic_id: UUID
    type: ExerciseType
    question: str
    prompt: str
    hint: str | None
    options: list[str] | None
    correct_index: int | None
    metadata: dict[str, Any]


class ExerciseSubmitRequest(BaseModel):
    """Request body for POST /api/exercises/{id}/submit."""

    answer: str | int
    used_hint: bool = False
    duration_seconds: int | None = Field(default=None, ge=1, le=600)


class ExerciseSubmissionResponse(BaseModel):
    """Response body after answer evaluation."""

    result: ExerciseResultType
    correct_answer: str
    explanation: str | None = None
    alternatives: list[str] = Field(default_factory=list)
    feedback: str
    mistakes: list[Mistake] = Field(default_factory=list)


class ExerciseHintResponse(BaseModel):
    """Response body returned by POST /api/exercises/{id}/hint."""

    hint: str


class ExerciseHistoryEntry(BaseModel):
    """Single exercise history entry."""

    id: UUID
    topic_id: UUID
    topic_name: str
    type: ExerciseType
    question: str
    prompt: str
    user_answer: str
    result: ExerciseResultType
    used_hint: bool
    duration_seconds: int | None
    completed_at: datetime

    model_config = ConfigDict(from_attributes=True)


class ExerciseHistoryResponse(BaseModel):
    """Paginated response for GET /api/exercises/history."""

    data: list[ExerciseHistoryEntry]
    pagination: PaginationMeta


__all__ = [
    "ExerciseGenerateRequest",
    "ExerciseHintResponse",
    "ExerciseHistoryEntry",
    "ExerciseHistoryResponse",
    "ExerciseSubmissionResponse",
    "ExerciseSubmitRequest",
    "GeneratedExerciseResponse",
    "PendingExercise",
]
