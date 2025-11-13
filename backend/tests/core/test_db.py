"""Tests for database module."""

from __future__ import annotations

import pytest

from app.core.db import get_session


@pytest.mark.asyncio
async def test_get_session_is_generator() -> None:
    """Test that get_session is a generator."""
    gen = get_session()
    assert hasattr(gen, "__anext__")


def test_database_url_from_settings() -> None:
    """Test that database URL comes from settings."""
    from app.core.config import settings

    assert settings.database_url is not None
    assert len(settings.database_url) > 0
