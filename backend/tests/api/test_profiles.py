from __future__ import annotations

import uuid
from datetime import datetime, timezone
from types import SimpleNamespace
from unittest.mock import AsyncMock

import pytest
from httpx import AsyncClient

from app.api.routes.profiles import get_language_profile_service
from app.core.auth import get_current_user
from app.main import app


class StubProfileService:
    """Test double mimicking LanguageProfileService."""

    def __init__(self) -> None:
        now = datetime.now(tz=timezone.utc)
        self.profile = SimpleNamespace(
            id=uuid.uuid4(),
            user_id=uuid.uuid4(),
            language="es",
            language_name="Испанский",
            current_level="A2",
            target_level="B1",
            goals=["travel"],
            interface_language="ru",
            is_active=True,
            streak=3,
            created_at=now,
            updated_at=now,
        )
        self.session = SimpleNamespace(commit=AsyncMock())

    async def list_profiles(self, user: object) -> list[SimpleNamespace]:
        return [self.profile]

    async def create_profile(self, user: object, payload: object) -> SimpleNamespace:
        self.last_payload = payload
        return self.profile

    async def get_profile(self, user: object, profile_id: uuid.UUID) -> SimpleNamespace:
        return self.profile

    async def update_profile(
        self, user: object, profile_id: uuid.UUID, payload: object
    ) -> SimpleNamespace:
        self.last_payload = payload
        return self.profile

    async def delete_profile(self, user: object, profile_id: uuid.UUID) -> None:
        self.deleted = profile_id

    async def activate_profile(self, user: object, profile_id: uuid.UUID) -> SimpleNamespace:
        self.profile.is_active = True
        return self.profile


@pytest.fixture()
def stub_user() -> SimpleNamespace:
    return SimpleNamespace(id=uuid.uuid4())


@pytest.fixture()
def profile_service_stub() -> StubProfileService:
    return StubProfileService()


@pytest.fixture(autouse=True)
def override_dependencies(
    stub_user: SimpleNamespace,
    profile_service_stub: StubProfileService,
) -> None:
    async def _user_override() -> SimpleNamespace:
        return stub_user

    async def _service_override() -> StubProfileService:
        return profile_service_stub

    app.dependency_overrides[get_current_user] = _user_override
    app.dependency_overrides[get_language_profile_service] = _service_override

    yield

    app.dependency_overrides.pop(get_current_user, None)
    app.dependency_overrides.pop(get_language_profile_service, None)


@pytest.mark.asyncio
async def test_list_profiles_returns_serialized_payload() -> None:
    async with AsyncClient(app=app, base_url="http://testserver") as client:
        response = await client.get("/api/profiles")

    assert response.status_code == 200
    payload = response.json()
    assert payload["data"][0]["language"] == "es"
    assert payload["data"][0]["progress"]["streak"] == 3


@pytest.mark.asyncio
async def test_create_profile_returns_201() -> None:
    async with AsyncClient(app=app, base_url="http://testserver") as client:
        response = await client.post(
            "/api/profiles",
            json={
                "language": "es",
                "current_level": "A2",
                "target_level": "B1",
                "goals": ["travel"],
                "interface_language": "ru",
            },
        )

    assert response.status_code == 201
    assert response.json()["language_name"] == "Испанский"


@pytest.mark.asyncio
async def test_activate_profile_returns_updated_payload(
    profile_service_stub: StubProfileService,
) -> None:
    profile_service_stub.profile.is_active = False

    async with AsyncClient(app=app, base_url="http://testserver") as client:
        response = await client.post(f"/api/profiles/{profile_service_stub.profile.id}/activate")

    assert response.status_code == 200
    assert response.json()["is_active"] is True


@pytest.mark.asyncio
async def test_delete_profile_returns_204() -> None:
    async with AsyncClient(app=app, base_url="http://testserver") as client:
        response = await client.delete(f"/api/profiles/{uuid.uuid4()}")

    assert response.status_code == 204
