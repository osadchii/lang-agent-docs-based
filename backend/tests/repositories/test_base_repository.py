"""Tests for base repository."""

from __future__ import annotations

from unittest.mock import AsyncMock

import pytest

from app.repositories.base import BaseRepository


@pytest.mark.asyncio
async def test_base_repository_add() -> None:
    """Test BaseRepository add method."""
    mock_session = AsyncMock()
    mock_session.add = AsyncMock()
    mock_session.flush = AsyncMock()

    repo = BaseRepository(mock_session)

    instance = object()
    result = await repo.add(instance)

    assert result is instance
    mock_session.add.assert_called_once_with(instance)
    mock_session.flush.assert_awaited_once()


@pytest.mark.asyncio
async def test_base_repository_session_access() -> None:
    """Test that BaseRepository stores session."""
    mock_session = AsyncMock()
    repo = BaseRepository(mock_session)

    assert repo.session is mock_session
