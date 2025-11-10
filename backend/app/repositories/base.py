"""Common helpers for repository implementations."""

from __future__ import annotations

from typing import Generic, TypeVar

from sqlalchemy.ext.asyncio import AsyncSession

ModelT = TypeVar("ModelT")


class BaseRepository(Generic[ModelT]):
    """Lightweight helper storing the AsyncSession dependency."""

    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def add(self, instance: ModelT) -> ModelT:
        self.session.add(instance)
        await self.session.flush()
        return instance


__all__ = ["BaseRepository"]
