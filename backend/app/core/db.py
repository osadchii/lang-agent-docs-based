"""Database engine and session configuration."""

from __future__ import annotations

from collections.abc import AsyncGenerator

from sqlalchemy.ext.asyncio import (
    AsyncEngine,
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)

from app.core.config import settings


def _build_engine() -> AsyncEngine:
    return create_async_engine(
        settings.database_url,
        echo=settings.debug,
        pool_pre_ping=True,
    )


engine: AsyncEngine = _build_engine()
AsyncSessionFactory = async_sessionmaker(engine, expire_on_commit=False)


async def get_session() -> AsyncGenerator[AsyncSession, None]:
    """FastAPI dependency that yields a scoped AsyncSession."""

    async with AsyncSessionFactory() as session:
        yield session


async def dispose_engine() -> None:
    """Close the global engine (used in application shutdown hooks or tests)."""

    await engine.dispose()


__all__ = ["AsyncSessionFactory", "dispose_engine", "engine", "get_session"]
