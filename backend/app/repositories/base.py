"""Common helpers for repository implementations."""

from __future__ import annotations

from collections.abc import Awaitable
from typing import Generic, TypeVar, cast

from sqlalchemy.ext.asyncio import AsyncSession

ModelT = TypeVar("ModelT")


class BaseRepository(Generic[ModelT]):
    """Lightweight helper storing the AsyncSession dependency."""

    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def add(self, instance: ModelT) -> ModelT:
        """Add model to session handling async mocks in tests."""
        add_result = cast(object, self.session.add(instance))
        if isinstance(add_result, Awaitable):
            await add_result
        await self.session.flush()
        return instance


__all__ = ["BaseRepository"]
