"""Speech-to-text integration built on top of OpenAI Whisper."""

from __future__ import annotations

import io
import json
import logging
from dataclasses import dataclass
from typing import Any, Literal, Mapping

from openai import (
    APIConnectionError,
    APIError,
    AsyncOpenAI,
    AuthenticationError,
    BadRequestError,
    OpenAIError,
    RateLimitError,
)
from openai._types import NOT_GIVEN
from tenacity import retry, retry_if_exception_type, stop_after_attempt, wait_exponential

logger = logging.getLogger("app.services.speech_to_text")

_LANGUAGE_CODE_ALIASES = {
    "gr": "el",  # Greek (ISO 639-1: el)
    "ua": "uk",  # Ukrainian
    "cn": "zh",  # Simplify legacy country codes
    "jp": "ja",  # Japanese
}


def _normalize_response_body(body: object | None) -> object | None:
    if body is None:
        return None
    if isinstance(body, (str, int, float, bool, dict, list)):
        return body
    return str(body)


def _build_openai_error_context(exc: OpenAIError) -> dict[str, Any]:
    extra: dict[str, Any] = {"error": str(exc), "error_type": type(exc).__name__}
    if isinstance(exc, APIError):
        extra["status_code"] = getattr(exc, "status_code", None)
        normalized_body = _normalize_response_body(exc.body)
        if normalized_body is not None:
            extra["response_body"] = normalized_body

        error_payload: dict[str, Any] | None = None
        if isinstance(normalized_body, dict):
            candidate = normalized_body.get("error")
            if isinstance(candidate, dict):
                error_payload = candidate
            else:
                error_payload = normalized_body

        extra["openai_code"] = exc.code or (error_payload.get("code") if error_payload else None)
        extra["openai_param"] = exc.param or (error_payload.get("param") if error_payload else None)
        extra["openai_type"] = exc.type or (error_payload.get("type") if error_payload else None)

        response = getattr(exc, "response", None)
        if response is not None:
            request_id = response.headers.get("x-request-id") if response.headers else None
            if request_id:
                extra["request_id"] = request_id
            reason = getattr(response, "reason_phrase", None)
            if reason:
                extra["reason"] = reason

    return extra


def _summarize_openai_error_context(
    context: Mapping[str, Any],
    *,
    max_response_chars: int = 400,
) -> str:
    ordered_keys = (
        "status_code",
        "openai_code",
        "openai_param",
        "openai_type",
        "error",
        "response_body",
        "reason",
        "request_id",
    )

    parts: list[str] = []
    for key in ordered_keys:
        value = context.get(key)
        if value is None or value == "":
            continue
        if key == "response_body":
            serialized = _stringify_value(value)
            if len(serialized) > max_response_chars:
                serialized = serialized[: max_response_chars - 3] + "..."
            parts.append(f"{key}={serialized}")
        else:
            parts.append(f"{key}={_stringify_value(value)}")

    return ", ".join(parts) if parts else "no-extra-context"


def _stringify_value(value: object) -> str:
    if isinstance(value, (dict, list)):
        try:
            return json.dumps(value, ensure_ascii=True, separators=(",", ":"))
        except TypeError:
            return str(value)
    return str(value)


@dataclass(slots=True)
class SpeechToTextResult:
    """Normalized result returned by Whisper transcription requests."""

    text: str
    detected_language: str | None


class SpeechToTextService:
    """Wrapper around OpenAI Whisper API with retries and logging."""

    def __init__(
        self,
        *,
        api_key: str,
        model: str = "whisper-1",
        default_timeout: float = 60.0,
        client: AsyncOpenAI | None = None,
    ) -> None:
        self.model = model
        self.default_timeout = default_timeout
        self.client = client or AsyncOpenAI(api_key=api_key, timeout=default_timeout)

        logger.info(
            "Speech-to-text service initialized",
            extra={"model": model, "timeout": default_timeout},
        )

    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=2, max=10),
        retry=retry_if_exception_type((RateLimitError, APIConnectionError, APIError)),
        reraise=True,
    )
    async def transcribe(
        self,
        audio_bytes: bytes,
        *,
        language_hint: str | None = None,
        response_format: Literal["json", "text", "srt", "verbose_json", "vtt"] = "verbose_json",
        timeout: float | None = None,
    ) -> SpeechToTextResult:
        """
        Transcribe a Telegram voice/audio payload using Whisper.

        Args:
            audio_bytes: Raw audio payload (e.g. OGG from Telegram voice messages)
            language_hint: Optional ISO-639-1 hint to improve accuracy
            response_format: Whisper response format (verbose_json exposes detected language)
            timeout: Optional per-request timeout override

        Returns:
            SpeechToTextResult with normalized transcript info.
        """
        if not audio_bytes:
            raise ValueError("audio_bytes cannot be empty")

        buffer = io.BytesIO(audio_bytes)
        buffer.name = "telegram-voice.ogg"

        normalized_language = self._normalize_language_hint(language_hint)

        try:
            response = await self.client.audio.transcriptions.create(
                model=self.model,
                file=buffer,
                language=normalized_language if normalized_language is not None else NOT_GIVEN,
                response_format=response_format,
                timeout=timeout or self.default_timeout,
            )
        except AuthenticationError as exc:
            context = _build_openai_error_context(exc)
            logger.error(
                "Whisper authentication failed | %s",
                _summarize_openai_error_context(context),
                extra=context,
            )
            raise
        except BadRequestError as exc:
            context = _build_openai_error_context(exc)
            logger.error(
                "Whisper bad request | %s",
                _summarize_openai_error_context(context),
                extra=context,
            )
            raise
        except RateLimitError as exc:
            context = _build_openai_error_context(exc)
            logger.warning(
                "Whisper rate limit exceeded, retrying | %s",
                _summarize_openai_error_context(context),
                extra=context,
            )
            raise
        except APIConnectionError as exc:
            context = _build_openai_error_context(exc)
            logger.warning(
                "Whisper connection issue, retrying | %s",
                _summarize_openai_error_context(context),
                extra=context,
            )
            raise
        except OpenAIError as exc:
            context = _build_openai_error_context(exc)
            logger.error(
                "Whisper API error | %s",
                _summarize_openai_error_context(context),
                extra=context,
            )
            raise

        text = (getattr(response, "text", "") or "").strip()
        detected_language = getattr(response, "language", None)

        logger.info(
            "Voice message transcribed",
            extra={
                "bytes": len(audio_bytes),
                "language_hint": language_hint,
                "detected_language": detected_language,
                "transcript_length": len(text),
            },
        )

        return SpeechToTextResult(text=text, detected_language=detected_language)

    def _normalize_language_hint(self, language_hint: str | None) -> str | None:
        if language_hint is None:
            return None
        normalized = _LANGUAGE_CODE_ALIASES.get(language_hint.lower(), language_hint.lower())
        return normalized


__all__ = ["SpeechToTextService", "SpeechToTextResult"]
