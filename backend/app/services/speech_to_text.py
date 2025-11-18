"""Speech-to-text integration built on top of OpenAI Whisper."""

from __future__ import annotations

import io
import logging
from dataclasses import dataclass
from typing import Literal

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

        try:
            response = await self.client.audio.transcriptions.create(
                model=self.model,
                file=buffer,
                language=language_hint if language_hint is not None else NOT_GIVEN,
                response_format=response_format,
                timeout=timeout or self.default_timeout,
            )
        except AuthenticationError as exc:
            logger.error("Whisper authentication failed", extra={"error": str(exc)})
            raise
        except BadRequestError as exc:
            logger.error("Whisper bad request", extra={"error": str(exc)})
            raise
        except RateLimitError as exc:
            logger.warning("Whisper rate limit exceeded, retrying", extra={"error": str(exc)})
            raise
        except APIConnectionError as exc:
            logger.warning("Whisper connection issue, retrying", extra={"error": str(exc)})
            raise
        except OpenAIError as exc:
            logger.error(
                "Whisper API error",
                extra={"error": str(exc), "error_type": type(exc).__name__},
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


__all__ = ["SpeechToTextService", "SpeechToTextResult"]
