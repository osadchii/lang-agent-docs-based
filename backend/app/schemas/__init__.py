"""Public exports for Pydantic schemas."""

from __future__ import annotations

from .dialog import ChatHistoryResponse, ChatMessage, ChatRequest, ChatResponse, PaginationMeta
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

__all__ = [
    "CEFRLevel",
    "CardContent",
    "ChatHistoryResponse",
    "ChatMessage",
    "ChatRequest",
    "ChatResponse",
    "ExerciseContent",
    "ExerciseResult",
    "IntentDetection",
    "LanguageProfileCreate",
    "LanguageProfileListResponse",
    "LanguageProfileProgress",
    "LanguageProfileResponse",
    "LanguageProfileUpdate",
    "Mistake",
    "PaginationMeta",
    "TopicSuggestion",
    "TopicSuggestions",
    "WordSuggestion",
    "WordSuggestions",
]
