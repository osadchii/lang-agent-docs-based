"""Media services for OCR and text suggestions backed by GPT-4 Vision."""

from __future__ import annotations

import base64
import importlib
import io
import logging
from dataclasses import dataclass
from typing import Literal, Sequence

from openai import (
    APIConnectionError,
    APIError,
    AsyncOpenAI,
    AuthenticationError,
    BadRequestError,
    OpenAIError,
    RateLimitError,
)
from openai.types.chat.chat_completion import ChatCompletion
from PIL import Image, ImageOps, UnidentifiedImageError
from pydantic import BaseModel, Field
from tenacity import retry, retry_if_exception_type, stop_after_attempt, wait_exponential

from app.core.errors import ApplicationError, ErrorCode
from app.services.llm import TokenUsage as LLMTokenUsage

logger = logging.getLogger("app.services.media")


def _register_heif_opener() -> None:
    """Try to enable HEIF/HEIC decoding via pillow-heif dynamically."""
    try:
        module = importlib.import_module("pillow_heif")
    except Exception as exc:  # pragma: no cover - optional dependency
        logger.debug("pillow-heif is unavailable", extra={"error": str(exc)})
        return

    register = getattr(module, "register_heif_opener", None)
    if callable(register):  # pragma: no branch - trivial check
        register()


_register_heif_opener()


@dataclass(slots=True)
class ImageInput:
    """Raw image payload received from the transport layer."""

    name: str
    content_type: str | None
    data: bytes


@dataclass(slots=True)
class ProcessedImage:
    """Image converted to a normalized JPEG with enforced bounds."""

    index: int
    content: bytes
    content_type: str


@dataclass(slots=True)
class OCRSegment:
    """Structured OCR output for a single image."""

    index: int
    full_text: str
    target_text: str
    detected_languages: list[str]
    contains_target_language: bool
    confidence: Literal["low", "medium", "high"]


@dataclass(slots=True)
class OCRAnalysis:
    """Result of OCR analysis across one or more images."""

    segments: list[OCRSegment]
    combined_text: str
    has_target_language: bool
    usage: LLMTokenUsage


class _VisionPayload(BaseModel):
    """JSON payload returned by GPT-4 Vision OCR prompt."""

    full_text: str = Field(default="", description="Full recognized text in any language.")
    target_text: str = Field(
        default="", description="Only fragments written in the requested target language."
    )
    detected_languages: list[str] = Field(
        default_factory=list, description="Detected ISO-639-1 language codes ordered by relevance."
    )
    contains_target_language: bool = Field(
        default=False, description="Whether target language text was found."
    )


class OCRService:
    """High level OCR service handling preprocessing and GPT-4 Vision calls."""

    _ALLOWED_CONTENT_TYPES = frozenset(
        {"image/jpeg", "image/png", "image/webp", "image/heic", "image/heif"}
    )

    def __init__(
        self,
        *,
        api_key: str,
        model: str = "gpt-4o-mini",
        max_images: int = 3,
        max_image_bytes: int = 10_485_760,
        max_image_dimension: int = 2048,
        max_output_tokens: int = 900,
        timeout: float = 60.0,
        client: AsyncOpenAI | None = None,
    ) -> None:
        self.model = model
        self.max_images = max_images
        self.max_image_bytes = max_image_bytes
        self.max_image_dimension = max_image_dimension
        self.max_output_tokens = max_output_tokens
        self._client = client or AsyncOpenAI(api_key=api_key, timeout=timeout)

        logger.info(
            "OCR service initialized",
            extra={
                "model": model,
                "max_images": max_images,
                "max_bytes": max_image_bytes,
                "max_dimension": max_image_dimension,
            },
        )

    async def analyze(
        self,
        images: Sequence[ImageInput],
        *,
        target_language_code: str,
        target_language_name: str,
    ) -> OCRAnalysis:
        """Analyze provided images and return extracted text per use-cases."""
        if not images:
            raise ApplicationError(
                code=ErrorCode.INVALID_FIELD_VALUE,
                message="Нужно прикрепить хотя бы одно изображение.",
            )
        if len(images) > self.max_images:
            raise ApplicationError(
                code=ErrorCode.INVALID_FIELD_VALUE,
                message=f"Можно отправить максимум {self.max_images} изображений за раз.",
            )

        processed = [self._prepare_image(image, index=i) for i, image in enumerate(images)]

        segments: list[OCRSegment] = []
        usage_total = LLMTokenUsage(0, 0, 0)

        for item in processed:
            payload, usage = await self._extract_text(
                item,
                target_language_code=target_language_code,
                target_language_name=target_language_name,
            )
            segment = OCRSegment(
                index=item.index,
                full_text=self._normalize_text(payload.full_text),
                target_text=self._normalize_text(payload.target_text),
                detected_languages=[lang.lower() for lang in payload.detected_languages],
                contains_target_language=payload.contains_target_language,
                confidence=self._confidence(payload.target_text or payload.full_text),
            )
            segments.append(segment)
            usage_total = self._accumulate_usage(usage_total, usage)

        combined_text = self._combine_segments(segments)
        has_target = any(
            segment.contains_target_language and segment.target_text for segment in segments
        )

        return OCRAnalysis(
            segments=segments,
            combined_text=combined_text,
            has_target_language=has_target,
            usage=usage_total,
        )

    def _prepare_image(self, payload: ImageInput, *, index: int) -> ProcessedImage:
        if len(payload.data) > self.max_image_bytes:
            raise ApplicationError(
                code=ErrorCode.PAYLOAD_TOO_LARGE,
                message=f"Изображение “{payload.name or 'image'}” превышает "
                f"{self.max_image_bytes // 1_000_000} МБ.",
            )

        content_type = (payload.content_type or "").lower()
        if content_type and content_type not in self._ALLOWED_CONTENT_TYPES:
            raise ApplicationError(
                code=ErrorCode.INVALID_FIELD_VALUE,
                message="Поддерживаются только изображения (JPG, PNG, WEBP, HEIC).",
            )

        try:
            image = Image.open(io.BytesIO(payload.data))
        except UnidentifiedImageError as exc:
            raise ApplicationError(
                code=ErrorCode.INVALID_FIELD_VALUE,
                message="Не удалось определить формат изображения.",
            ) from exc

        image = ImageOps.exif_transpose(image)
        if max(image.size) > self.max_image_dimension:
            ratio = self.max_image_dimension / max(image.size)
            new_size = (max(1, int(image.width * ratio)), max(1, int(image.height * ratio)))
            image = image.resize(new_size, Image.LANCZOS)

        if image.mode not in {"RGB", "L"}:
            image = image.convert("RGB")

        buffer = io.BytesIO()
        image.save(buffer, format="JPEG", optimize=True, quality=90)
        return ProcessedImage(index=index, content=buffer.getvalue(), content_type="image/jpeg")

    def _combine_segments(self, segments: Sequence[OCRSegment]) -> str:
        texts: list[str] = []
        for segment in segments:
            candidate = segment.target_text or segment.full_text
            if candidate:
                texts.append(candidate)
        combined = "\n\n".join(texts).strip()
        return combined

    def _normalize_text(self, text: str, *, limit: int = 4000) -> str:
        cleaned = " ".join(text.split())
        if not cleaned:
            return ""
        if len(cleaned) > limit:
            return cleaned[: limit - 1].rstrip() + "…"
        return cleaned

    def _confidence(self, text: str) -> Literal["low", "medium", "high"]:
        length = len(text.strip())
        if length >= 160:
            return "high"
        if length >= 60:
            return "medium"
        return "low"

    def _accumulate_usage(self, left: LLMTokenUsage, right: LLMTokenUsage) -> LLMTokenUsage:
        return LLMTokenUsage(
            left.prompt_tokens + right.prompt_tokens,
            left.completion_tokens + right.completion_tokens,
            left.total_tokens + right.total_tokens,
        )

    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=2, max=10),
        retry=retry_if_exception_type((APIConnectionError, APIError, RateLimitError)),
        reraise=True,
    )
    async def _extract_text(
        self,
        image: ProcessedImage,
        *,
        target_language_code: str,
        target_language_name: str,
    ) -> tuple[_VisionPayload, LLMTokenUsage]:
        image_url = f"data:{image.content_type};base64,{base64.b64encode(image.content).decode()}"
        prompt = (
            "You are an OCR engine. Extract all text from the image and respond in JSON with "
            "keys full_text, target_text, detected_languages (ISO-639-1 codes) and "
            "contains_target_language (boolean). "
            f"The learner studies {target_language_name} (language code {target_language_code}). "
            "The target_text field must contain only fragments in the target language while "
            "preserving original line order."
        )

        try:
            response: ChatCompletion = await self._client.chat.completions.create(
                model=self.model,
                temperature=0,
                max_tokens=self.max_output_tokens,
                response_format={"type": "json_object"},
                messages=[
                    {"role": "system", "content": "You convert images into clean text responses."},
                    {
                        "role": "user",
                        "content": [
                            {"type": "text", "text": prompt},
                            {
                                "type": "image_url",
                                "image_url": {"url": image_url, "detail": "high"},
                            },
                        ],
                    },
                ],
            )
        except AuthenticationError as exc:
            logger.error("Vision authentication failed", extra={"error": str(exc)})
            raise
        except BadRequestError as exc:  # pragma: no cover - validated via smoke tests
            logger.error("Vision bad request", extra={"error": str(exc)})
            raise
        except OpenAIError as exc:
            logger.error(
                "Vision API error",
                extra={"error": str(exc), "error_type": type(exc).__name__},
            )
            raise ApplicationError(
                code=ErrorCode.LLM_SERVICE_ERROR,
                message="Не удалось распознать изображение, попробуйте позже.",
            ) from exc

        content = response.choices[0].message.content or "{}"
        payload = _VisionPayload.model_validate_json(content)
        usage = self._usage_from_response(response)

        logger.info(
            "OCR completed",
            extra={
                "image_index": image.index,
                "has_target": payload.contains_target_language,
                "detected_languages": payload.detected_languages,
            },
        )

        return payload, usage

    def _usage_from_response(self, response: ChatCompletion) -> LLMTokenUsage:
        usage = response.usage
        if usage is None:
            return LLMTokenUsage(0, 0, 0)
        return LLMTokenUsage(
            prompt_tokens=usage.prompt_tokens or 0,
            completion_tokens=usage.completion_tokens or 0,
            total_tokens=usage.total_tokens or 0,
        )


__all__ = ["ImageInput", "OCRAnalysis", "OCRSegment", "OCRService"]
