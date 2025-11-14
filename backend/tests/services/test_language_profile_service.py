from __future__ import annotations

import uuid
from datetime import datetime, timezone

import pytest
import pytest_asyncio
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.errors import ApplicationError, ErrorCode
from app.models.user import User
from app.repositories.language_profile import LanguageProfileRepository
from app.schemas.profile import LanguageProfileCreate
from app.services.language_profile import LanguageProfileService


@pytest_asyncio.fixture()
async def service(db_session: AsyncSession) -> LanguageProfileService:
    repository = LanguageProfileRepository(db_session)
    return LanguageProfileService(repository)


@pytest_asyncio.fixture()
async def user(db_session: AsyncSession) -> User:
    instance = User(
        id=uuid.uuid4(),
        telegram_id=123456,
        first_name="Test",
        created_at=datetime.now(tz=timezone.utc),
        updated_at=datetime.now(tz=timezone.utc),
    )
    db_session.add(instance)
    await db_session.flush()
    return instance


def _payload(
    *,
    language: str = "es",
    current: str = "A2",
    target: str = "B1",
) -> LanguageProfileCreate:
    return LanguageProfileCreate(
        language=language,
        current_level=current,
        target_level=target,
        goals=["travel", "communication"],
        interface_language="ru",
    )


@pytest.mark.asyncio
async def test_create_profile_sets_language_name_and_activation(
    service: LanguageProfileService, user: User
) -> None:
    profile = await service.create_profile(user, _payload())

    assert profile.language_name == "Испанский"
    assert profile.is_active is True
    assert profile.interface_language == "ru"


@pytest.mark.asyncio
async def test_create_profile_rejects_duplicate_language(
    service: LanguageProfileService, user: User
) -> None:
    user.is_premium = True
    await service.create_profile(user, _payload(language="es"))

    with pytest.raises(ApplicationError) as exc:
        await service.create_profile(user, _payload(language="es"))

    assert exc.value.code == ErrorCode.DUPLICATE_LANGUAGE


@pytest.mark.asyncio
async def test_free_plan_allows_only_single_profile(
    service: LanguageProfileService, user: User
) -> None:
    await service.create_profile(user, _payload(language="es"))

    with pytest.raises(ApplicationError) as exc:
        await service.create_profile(user, _payload(language="de"))

    assert exc.value.code == ErrorCode.LIMIT_REACHED


@pytest.mark.asyncio
async def test_activate_profile_switches_active_flag(
    service: LanguageProfileService, user: User
) -> None:
    user.is_premium = True
    first = await service.create_profile(user, _payload(language="es"))
    second = await service.create_profile(user, _payload(language="de"))

    assert second.is_active is False

    activated = await service.activate_profile(user, second.id)
    await service.session.refresh(first)

    assert activated.is_active is True
    assert first.is_active is False


@pytest.mark.asyncio
async def test_delete_profile_requires_at_least_one_remaining(
    service: LanguageProfileService, user: User
) -> None:
    user.is_premium = True
    primary = await service.create_profile(user, _payload(language="es"))
    backup = await service.create_profile(user, _payload(language="de"))

    await service.delete_profile(user, primary.id)
    await service.session.refresh(backup)

    assert backup.is_active is True

    with pytest.raises(ApplicationError) as exc:
        await service.delete_profile(user, backup.id)

    assert exc.value.code == ErrorCode.LAST_PROFILE
