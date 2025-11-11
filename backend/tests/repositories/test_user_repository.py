from __future__ import annotations

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from app.repositories.user import UserRepository


@pytest.mark.asyncio
async def test_user_repository_create_and_fetch(db_session: AsyncSession) -> None:
    repo = UserRepository(db_session)

    created = await repo.create(telegram_id=123456, first_name="Alice")
    fetched = await repo.get_by_telegram_id(123456)

    assert fetched is not None
    assert fetched.id == created.id
    assert fetched.first_name == "Alice"


@pytest.mark.asyncio
async def test_user_repository_soft_delete_and_list(db_session: AsyncSession) -> None:
    repo = UserRepository(db_session)

    u1 = await repo.create(telegram_id=1, first_name="User1")
    await repo.create(telegram_id=2, first_name="User2")

    await repo.soft_delete(u1.id)

    users = await repo.list_active()
    assert len(users) == 1
    assert users[0].telegram_id == 2
