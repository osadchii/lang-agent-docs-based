from __future__ import annotations

import os
from typing import Final

import pytest_asyncio
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.pool import StaticPool

from app.models.base import Base

_TEST_ENV_VARS: Final[dict[str, str]] = {
    "APP_ENV": "test",
    "DATABASE_URL": "sqlite+aiosqlite:///:memory:",
    "REDIS_URL": "redis://localhost:6379/0",
    "SECRET_KEY": "test-secret",
    "TELEGRAM_BOT_TOKEN": "000000:test",
    "OPENAI_API_KEY": "sk-test",
}

for key, value in _TEST_ENV_VARS.items():
    os.environ.setdefault(key, value)


@pytest_asyncio.fixture()
async def db_session() -> AsyncSession:
    engine = create_async_engine(
        "sqlite+aiosqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )

    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    Session = async_sessionmaker(engine, expire_on_commit=False)

    async with Session() as session:
        yield session

    await engine.dispose()
