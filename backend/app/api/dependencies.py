"""Shared FastAPI dependency builders."""

from __future__ import annotations

from app.core.cache import CacheClient
from app.core.config import settings
from app.services.llm_enhanced import EnhancedLLMService

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


__all__ = ["build_enhanced_llm_service", "get_cache_client"]
