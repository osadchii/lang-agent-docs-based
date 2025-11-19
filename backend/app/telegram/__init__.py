"""Telegram bot bindings used across the backend."""

from __future__ import annotations

from app.core.cache import CacheClient
from app.core.config import settings
from app.services.media import OCRService
from app.services.speech_to_text import SpeechToTextService
from app.telegram.bot import TelegramBot

speech_to_text_service = SpeechToTextService(
    api_key=settings.openai_api_key.get_secret_value(),
    model=settings.voice_transcription_model,
    default_timeout=settings.voice_transcription_timeout,
)

ocr_service = OCRService(
    api_key=settings.openai_api_key.get_secret_value(),
    model=settings.ocr_vision_model,
    max_images=settings.ocr_max_images,
    max_image_bytes=settings.ocr_max_image_bytes,
    max_image_dimension=settings.ocr_max_image_dimension,
    max_output_tokens=settings.ocr_max_output_tokens,
    timeout=settings.ocr_vision_timeout,
)

cache_client = CacheClient(settings.redis_url)

telegram_bot = TelegramBot(
    token=settings.telegram_bot_token.get_secret_value(),
    environment=settings.environment,
    speech_to_text_service=speech_to_text_service,
    max_voice_duration_seconds=settings.voice_max_duration_seconds,
    max_voice_file_size_bytes=settings.voice_max_file_size_bytes,
    ocr_service=ocr_service,
    cache_client=cache_client,
    max_image_file_size_bytes=settings.ocr_max_image_bytes,
)

__all__ = ["telegram_bot", "TelegramBot"]
