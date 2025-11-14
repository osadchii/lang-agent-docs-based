from __future__ import annotations

import uuid
from datetime import datetime, timezone
from types import SimpleNamespace

import pytest
from httpx import AsyncClient

from app.api.routes.decks import get_deck_service
from app.core.auth import get_current_user
from app.main import app


class DeckServiceStub:
    def __init__(self) -> None:
        now = datetime.now(tz=timezone.utc)
        owner = SimpleNamespace(first_name="Maria", username=None, last_name=None)
        self.deck = SimpleNamespace(
            id=uuid.uuid4(),
            profile_id=uuid.uuid4(),
            name="Everyday words",
            description=None,
            is_active=True,
            is_group=False,
            owner_id=uuid.uuid4(),
            owner=owner,
            cards_count=20,
            new_cards_count=5,
            due_cards_count=3,
            created_at=now,
            updated_at=now,
        )

    async def list_decks(
        self, user: object, *, profile_id: object, include_group: bool
    ) -> list[SimpleNamespace]:
        self.last_profile_id = profile_id
        self.include_group = include_group
        return [self.deck]


@pytest.fixture()
def stub_user() -> SimpleNamespace:
    return SimpleNamespace(id=uuid.uuid4())


@pytest.fixture()
def deck_service_stub() -> DeckServiceStub:
    return DeckServiceStub()


@pytest.fixture(autouse=True)
def _override_dependencies(
    stub_user: SimpleNamespace,
    deck_service_stub: DeckServiceStub,
) -> None:
    async def _user_override() -> SimpleNamespace:
        return stub_user

    async def _service_override() -> DeckServiceStub:
        return deck_service_stub

    app.dependency_overrides[get_current_user] = _user_override
    app.dependency_overrides[get_deck_service] = _service_override
    yield
    app.dependency_overrides.pop(get_current_user, None)
    app.dependency_overrides.pop(get_deck_service, None)


@pytest.mark.asyncio
async def test_list_decks_returns_serialized_payload(deck_service_stub: DeckServiceStub) -> None:
    async with AsyncClient(app=app, base_url="http://testserver") as client:
        response = await client.get("/api/decks")

    assert response.status_code == 200
    payload = response.json()
    assert payload["data"][0]["name"] == "Everyday words"
    assert payload["data"][0]["owner_name"] == "Maria"
    assert deck_service_stub.include_group is True
