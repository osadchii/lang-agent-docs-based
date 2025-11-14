from __future__ import annotations

import uuid
from datetime import datetime, timezone
from types import SimpleNamespace

import pytest
from httpx import AsyncClient

from app.api.routes.cards import get_card_service
from app.core.auth import get_current_user
from app.main import app


class CardServiceStub:
    def __init__(self) -> None:
        now = datetime.now(tz=timezone.utc)
        self.card = SimpleNamespace(
            id=uuid.uuid4(),
            deck_id=uuid.uuid4(),
            word="casa",
            translation="дом",
            example="Mi casa es tu casa",
            example_translation="Мой дом - твой дом",
            lemma="casa",
            notes=None,
            status="new",
            interval_days=0,
            next_review=now,
            reviews_count=0,
            ease_factor=2.5,
            last_rating=None,
            last_reviewed_at=None,
            created_at=now,
            updated_at=now,
        )

    async def list_cards(
        self,
        user: object,
        *,
        deck_id: uuid.UUID,
        status: str | None,
        search: str | None,
        limit: int,
        offset: int,
    ) -> tuple[list[SimpleNamespace], int]:
        self.last_call = {
            "deck_id": deck_id,
            "status": status,
            "search": search,
            "limit": limit,
            "offset": offset,
        }
        return [self.card], 1

    async def get_card(self, user: object, card_id: uuid.UUID) -> SimpleNamespace:
        self.last_card_id = card_id
        return self.card


@pytest.fixture()
def stub_user() -> SimpleNamespace:
    return SimpleNamespace(id=uuid.uuid4())


@pytest.fixture()
def card_service_stub() -> CardServiceStub:
    return CardServiceStub()


@pytest.fixture(autouse=True)
def _overrides(
    stub_user: SimpleNamespace,
    card_service_stub: CardServiceStub,
) -> None:
    async def _user_override() -> SimpleNamespace:
        return stub_user

    async def _service_override() -> CardServiceStub:
        return card_service_stub

    app.dependency_overrides[get_current_user] = _user_override
    app.dependency_overrides[get_card_service] = _service_override
    yield
    app.dependency_overrides.pop(get_current_user, None)
    app.dependency_overrides.pop(get_card_service, None)


@pytest.mark.asyncio
async def test_list_cards_returns_data(card_service_stub: CardServiceStub) -> None:
    async with AsyncClient(app=app, base_url="http://testserver") as client:
        response = await client.get(
            "/api/cards",
            params={"deck_id": str(card_service_stub.card.deck_id), "limit": 5},
        )

    assert response.status_code == 200
    payload = response.json()
    assert payload["data"][0]["word"] == "casa"
    assert payload["pagination"]["count"] == 1
    assert card_service_stub.last_call["limit"] == 5


@pytest.mark.asyncio
async def test_get_card_returns_single_payload(card_service_stub: CardServiceStub) -> None:
    target_id = uuid.uuid4()
    async with AsyncClient(app=app, base_url="http://testserver") as client:
        response = await client.get(f"/api/cards/{target_id}")

    assert response.status_code == 200
    assert response.json()["lemma"] == "casa"
    assert card_service_stub.last_card_id == target_id
