from __future__ import annotations

import uuid
from datetime import datetime, timezone
from types import SimpleNamespace

import pytest
from httpx import AsyncClient

from app.api.routes.cards import get_card_service, get_llm_service
from app.core.auth import get_current_user
from app.main import app
from app.schemas.card import CardCreateResult, RateCardRequest


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
        self.created_result = CardCreateResult(created=[self.card], duplicates=[], failed=[])
        self.next_card: SimpleNamespace | None = self.card
        self.rate_payload: RateCardRequest | None = None

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

    async def create_cards(
        self,
        user: object,
        payload: object,
        *,
        llm_service: object,
    ) -> CardCreateResult:
        self.created_payload = payload
        self.used_llm = llm_service
        return self.created_result

    async def get_next_card(
        self, user: object, *, deck_id: uuid.UUID | None = None
    ) -> SimpleNamespace | None:
        self.next_deck_id = deck_id
        return self.next_card

    async def rate_card(self, user: object, payload: RateCardRequest) -> SimpleNamespace:
        self.rate_payload = payload
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

    async def _llm_override() -> SimpleNamespace:
        return SimpleNamespace()

    app.dependency_overrides[get_current_user] = _user_override
    app.dependency_overrides[get_card_service] = _service_override
    app.dependency_overrides[get_llm_service] = _llm_override
    yield
    app.dependency_overrides.pop(get_current_user, None)
    app.dependency_overrides.pop(get_card_service, None)
    app.dependency_overrides.pop(get_llm_service, None)


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


@pytest.mark.asyncio
async def test_create_cards_returns_result(card_service_stub: CardServiceStub) -> None:
    async with AsyncClient(app=app, base_url="http://testserver") as client:
        response = await client.post(
            "/api/cards",
            json={"deck_id": str(card_service_stub.card.deck_id), "words": ["casa"]},
        )

    assert response.status_code == 201
    body = response.json()
    assert body["created"][0]["lemma"] == "casa"
    assert card_service_stub.created_payload.words == ["casa"]


@pytest.mark.asyncio
async def test_next_card_returns_204_when_empty(card_service_stub: CardServiceStub) -> None:
    card_service_stub.next_card = None
    async with AsyncClient(app=app, base_url="http://testserver") as client:
        response = await client.get("/api/cards/next")

    assert response.status_code == 204


@pytest.mark.asyncio
async def test_rate_card_returns_updated_fields(card_service_stub: CardServiceStub) -> None:
    async with AsyncClient(app=app, base_url="http://testserver") as client:
        response = await client.post(
            "/api/cards/rate",
            json={"card_id": str(card_service_stub.card.id), "rating": "know"},
        )

    assert response.status_code == 200
    payload = response.json()
    assert payload["interval_days"] == card_service_stub.card.interval_days
    assert card_service_stub.rate_payload.card_id == card_service_stub.card.id
