"""
Pydantic schemas for structured LLM responses.

This module contains response models for parsing and validating JSON outputs
from LLM API calls, ensuring type safety and data integrity.
"""

from __future__ import annotations

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

__all__ = [
    "CardContent",
    "ExerciseContent",
    "ExerciseResult",
    "IntentDetection",
    "Mistake",
    "TopicSuggestion",
    "TopicSuggestions",
    "WordSuggestion",
    "WordSuggestions",
]
