"""Pydantic schemas for OCR/media endpoints."""

from __future__ import annotations

from typing import Literal
from uuid import UUID

from pydantic import BaseModel, Field

from app.schemas.llm_responses import WordSuggestion


class OCRSegmentPayload(BaseModel):
    """Segment-level OCR payload returned to the client."""

    image_index: int = Field(ge=0, description="Position of the processed image in the request.")
    detected_languages: list[str] = Field(
        default_factory=list, description="ISO-639-1 codes detected on the image."
    )
    contains_target_language: bool = Field(
        description="Indicates if text in the learner's language was found."
    )
    confidence: Literal["low", "medium", "high"] = Field(
        description="Approximate confidence based on extracted text length."
    )
    full_text: str = Field(description="Recognized text without filtering by language.")
    target_text: str = Field(
        description="Recognized text filtered to the learner's language (may be empty)."
    )


class OCRAnalyzeResponse(BaseModel):
    """Response body for POST /api/media/ocr endpoint."""

    profile_id: UUID
    target_language: str = Field(description="Target language ISO-639-1 code.")
    target_language_name: str = Field(description="Human-readable language name.")
    combined_text: str = Field(
        description="Concatenated result across images (target language when available)."
    )
    has_target_language: bool = Field(
        description="Whether any of the uploaded images contained target language text."
    )
    detected_languages: list[str] = Field(
        default_factory=list,
        description="Union of detected languages across all uploaded images.",
    )
    segments: list[OCRSegmentPayload] = Field(
        description="Per-image OCR metadata and extracted text."
    )
    suggestions: list[WordSuggestion] = Field(
        default_factory=list,
        description="Words/phrases suggested for adding to flashcards.",
    )


__all__ = ["OCRAnalyzeResponse", "OCRSegmentPayload"]
