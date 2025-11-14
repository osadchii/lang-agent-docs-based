"""Public exports for Pydantic schemas."""

from __future__ import annotations

from .card import CardListResponse, CardResponse
from .deck import DeckListResponse, DeckSummary
from .dialog import ChatHistoryResponse, ChatMessage, ChatRequest, ChatResponse, PaginationMeta
from .exercise import (
    ExerciseGenerateRequest,
    ExerciseHintResponse,
    ExerciseHistoryEntry,
    ExerciseHistoryResponse,
    ExerciseSubmissionResponse,
    ExerciseSubmitRequest,
    GeneratedExerciseResponse,
    PendingExercise,
)
from .llm_responses import (
    CardContent,
    ExerciseContent,
    ExerciseResult,
    IntentDetection,
    Mistake,
    TopicSuggestion,
    TopicSuggestions,
    WordSuggestion,
    WordSuggestions,
)
from .profile import (
    CEFRLevel,
    LanguageProfileCreate,
    LanguageProfileListResponse,
    LanguageProfileProgress,
    LanguageProfileResponse,
    LanguageProfileUpdate,
)
from .topic import (
    TopicCreateRequest,
    TopicDetail,
    TopicListResponse,
    TopicResponse,
    TopicSuggestRequest,
    TopicSuggestResponse,
    TopicSummary,
    TopicUpdateRequest,
)

__all__ = [
    "CEFRLevel",
    "CardContent",
    "CardListResponse",
    "CardResponse",
    "ChatHistoryResponse",
    "ChatMessage",
    "ChatRequest",
    "ChatResponse",
    "DeckListResponse",
    "DeckSummary",
    "ExerciseContent",
    "ExerciseGenerateRequest",
    "ExerciseHintResponse",
    "ExerciseHistoryEntry",
    "ExerciseHistoryResponse",
    "ExerciseResult",
    "ExerciseSubmissionResponse",
    "ExerciseSubmitRequest",
    "GeneratedExerciseResponse",
    "IntentDetection",
    "LanguageProfileCreate",
    "LanguageProfileListResponse",
    "LanguageProfileProgress",
    "LanguageProfileResponse",
    "LanguageProfileUpdate",
    "Mistake",
    "PaginationMeta",
    "PendingExercise",
    "TopicCreateRequest",
    "TopicDetail",
    "TopicListResponse",
    "TopicResponse",
    "TopicSuggestRequest",
    "TopicSuggestResponse",
    "TopicSuggestion",
    "TopicSuggestions",
    "TopicSummary",
    "TopicUpdateRequest",
    "WordSuggestion",
    "WordSuggestions",
]
