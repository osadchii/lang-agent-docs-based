"""
Pydantic models for structured LLM responses.

These models define the expected JSON structure from LLM API responses,
providing validation, type safety, and parsing capabilities.
"""

from __future__ import annotations

from typing import ClassVar, Literal

from pydantic import BaseModel, Field, field_validator


class CardContent(BaseModel):
    """Generated flashcard content from LLM."""

    word: str = Field(description="Word or phrase in target language")
    lemma: str = Field(description="Base form of the word")
    translation: str = Field(description="Translation to interface language")
    example: str = Field(description="Example sentence in target language")
    example_translation: str = Field(description="Translation of example sentence")
    notes: str | None = Field(default=None, description="Additional notes or context")


class ExerciseContent(BaseModel):
    """Generated exercise content from LLM."""

    question: str = Field(description="Exercise question or instruction")
    prompt: str = Field(description="Sentence to translate or complete")
    correct_answer: str = Field(description="Correct answer")
    hint: str | None = Field(default=None, description="Hint for the user")
    explanation: str = Field(description="Explanation of the grammar/vocabulary")
    alternatives: list[str] = Field(default_factory=list, description="Alternative correct answers")
    options: list[str] | None = Field(
        default=None, description="Options for multiple choice (if applicable)"
    )
    correct_index: int | None = Field(
        default=None, description="Index of correct option (for multiple choice)"
    )


class Mistake(BaseModel):
    """Detailed mistake information in exercise result."""

    type: Literal["grammar", "vocabulary", "spelling", "other"] = Field(
        description="Type of mistake"
    )
    description: str = Field(description="Description of what went wrong")
    suggestion: str = Field(description="Suggestion for improvement")


class ExerciseResult(BaseModel):
    """Result of exercise answer check from LLM."""

    result: Literal["correct", "partial", "incorrect"] = Field(description="Evaluation result")
    explanation: str = Field(description="Explanation of the result")
    correct_answer: str = Field(description="The correct answer")
    alternatives: list[str] = Field(default_factory=list, description="Alternative correct answers")
    feedback: str = Field(description="Encouraging feedback for the user")
    mistakes: list[Mistake] = Field(default_factory=list, description="List of mistakes")


class IntentDetection(BaseModel):
    """Detected user intent from message."""

    intent: Literal[
        "translate",
        "explain_grammar",
        "check_text",
        "add_card",
        "practice",
        "general",
        "off_topic",
    ] = Field(description="Detected intent")
    confidence: float = Field(ge=0.0, le=1.0, description="Confidence score")
    entities: dict[str, str] = Field(
        default_factory=dict, description="Extracted entities (word, context, etc.)"
    )


class TopicSuggestion(BaseModel):
    """Single topic suggestion for learning."""

    name: str = Field(description="Topic name in interface language")
    description: str = Field(description="Brief description of the topic")
    type: Literal["grammar", "vocabulary", "situation"] = Field(description="Topic type")
    reason: str = Field(description="Why this topic is relevant for the student")
    examples: list[str] = Field(description="2-3 example exercises or concepts")


class TopicSuggestions(BaseModel):
    """List of topic suggestions from LLM."""

    topics: list[TopicSuggestion] = Field(description="Suggested topics")


class WordSuggestion(BaseModel):
    """Single word suggestion from text analysis."""

    word: str = Field(description="Word or phrase to add")
    type: Literal["verb", "noun", "adjective", "adverb", "phrase", "other"] = Field(
        description="Word type"
    )
    reason: str = Field(description="Why this word is useful")
    priority: int = Field(ge=1, le=10, description="Priority (1=highest)")

    _TYPE_ALIASES: ClassVar[dict[str, str]] = {
        "preposition": "other",
        "conjunction": "other",
        "pronoun": "other",
        "article": "other",
        "determiner": "other",
        "interjection": "other",
        "particle": "other",
    }

    @field_validator("type", mode="before")
    @classmethod
    def _normalize_type(cls, value: object) -> str:
        if isinstance(value, str):
            normalized = value.lower().strip()
            if normalized in {"verb", "noun", "adjective", "adverb", "phrase", "other"}:
                return normalized
            return cls._TYPE_ALIASES.get(normalized, "other")
        return "other"


class WordSuggestions(BaseModel):
    """List of word suggestions from text (OCR/image)."""

    suggestions: list[WordSuggestion] = Field(description="Suggested words")


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
