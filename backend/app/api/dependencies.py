"""Shared FastAPI dependency builders."""

from __future__ import annotations

from app.core.cache import CacheClient
from app.core.config import settings
from app.services.llm_enhanced import EnhancedLLMService
from app.services.media import OCRService

_cache_client = CacheClient(settings.redis_url)


async def get_cache_client() -> CacheClient:
    """Return a singleton cache client (connect lazily)."""
    await _cache_client.connect()
    return _cache_client


def build_enhanced_llm_service(cache: CacheClient) -> EnhancedLLMService:
    """Factory helper for EnhancedLLMService."""
    return EnhancedLLMService(
        api_key=settings.openai_api_key.get_secret_value(),
        cache=cache,
        model=settings.llm_model,
        temperature=settings.llm_temperature,
    )


def build_ocr_service() -> OCRService:
    """Factory helper for OCRService."""
    return OCRService(
        api_key=settings.openai_api_key.get_secret_value(),
        model=settings.ocr_vision_model,
        max_images=settings.ocr_max_images,
        max_image_bytes=settings.ocr_max_image_bytes,
        max_image_dimension=settings.ocr_max_image_dimension,
        max_output_tokens=settings.ocr_max_output_tokens,
        timeout=settings.ocr_vision_timeout,
    )


__all__ = ["build_enhanced_llm_service", "build_ocr_service", "get_cache_client"]
