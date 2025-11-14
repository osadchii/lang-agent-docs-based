from __future__ import annotations

import uuid
from collections.abc import Iterator
from datetime import datetime, timezone
from types import SimpleNamespace
from unittest.mock import AsyncMock

import pytest
from httpx import AsyncClient

from app.api.routes.topics import get_topic_service
from app.core.auth import get_current_user
from app.main import app
from app.schemas.llm_responses import TopicSuggestion, TopicSuggestions


class TopicServiceStub:
    def __init__(self) -> None:
        now = datetime.now(tz=timezone.utc)
        self.topic = SimpleNamespace(
            id=uuid.uuid4(),
            profile_id=uuid.uuid4(),
            name="Pret�rito Perfecto",
            description="????????? ?????",
            type="grammar",
            is_active=True,
            is_group=False,
            owner_id=uuid.uuid4(),
            owner=SimpleNamespace(username="sensei", first_name=None, last_name=None),
            exercises_count=5,
            accuracy=0.8,
            created_at=now,
            updated_at=now,
            correct_count=4,
            partial_count=1,
            incorrect_count=0,
        )
        self.session = SimpleNamespace(commit=AsyncMock())

    async def list_topics(self, *args, **kwargs) -> list[SimpleNamespace]:  # noqa: ANN002, ANN003
        self.last_list_kwargs = kwargs
        return [self.topic]

    async def create_topic(self, user: object, payload: object) -> SimpleNamespace:
        self.last_payload = payload
        return self.topic

    async def get_topic(self, user: object, topic_id: uuid.UUID) -> SimpleNamespace:
        return self.topic

    async def update_topic(
        self, user: object, topic_id: uuid.UUID, payload: object
    ) -> SimpleNamespace:
        self.last_update_payload = payload
        return self.topic

    async def delete_topic(self, user: object, topic_id: uuid.UUID) -> None:
        self.deleted = topic_id

    async def activate_topic(self, user: object, topic_id: uuid.UUID) -> SimpleNamespace:
        self.topic.is_active = True
        return self.topic

    async def suggest_topics(
        self,
        user: object,
        request: object,
    ) -> TopicSuggestions:
        self.last_suggest_payload = request
        suggestion = TopicSuggestion(
            name="Ser vs Estar",
            description="???????? ????? ser ? estar",
            type="grammar",
            reason="?? ???????? ???????, ???? A2",
            examples=["Estoy cansado", "Soy alto"],
        )
        return TopicSuggestions(topics=[suggestion])


@pytest.fixture()
def stub_user() -> SimpleNamespace:
    return SimpleNamespace(id=uuid.uuid4())


@pytest.fixture()
def topic_service_stub() -> TopicServiceStub:
    return TopicServiceStub()


@pytest.fixture(autouse=True)
def _overrides(
    stub_user: SimpleNamespace,
    topic_service_stub: TopicServiceStub,
) -> Iterator[None]:
    async def _user_override() -> SimpleNamespace:
        return stub_user

    async def _service_override() -> TopicServiceStub:
        return topic_service_stub

    app.dependency_overrides[get_current_user] = _user_override
    app.dependency_overrides[get_topic_service] = _service_override
    yield
    app.dependency_overrides.pop(get_current_user, None)
    app.dependency_overrides.pop(get_topic_service, None)


@pytest.mark.asyncio
async def test_list_topics_returns_data() -> None:
    async with AsyncClient(app=app, base_url="http://testserver") as client:
        response = await client.get("/api/topics")

    assert response.status_code == 200
    payload = response.json()
    assert payload["data"][0]["name"] == "Pret�rito Perfecto"
    assert payload["data"][0]["owner_name"] == "sensei"


@pytest.mark.asyncio
async def test_create_topic_returns_201(topic_service_stub: TopicServiceStub) -> None:
    async with AsyncClient(app=app, base_url="http://testserver") as client:
        response = await client.post(
            "/api/topics",
            json={
                "profile_id": str(topic_service_stub.topic.profile_id),
                "name": "New topic",
                "type": "grammar",
            },
        )

    assert response.status_code == 201
    assert response.json()["name"] == "Pret�rito Perfecto"


@pytest.mark.asyncio
async def test_suggest_topics_returns_payload(topic_service_stub: TopicServiceStub) -> None:
    async with AsyncClient(app=app, base_url="http://testserver") as client:
        response = await client.post(
            "/api/topics/suggest",
            json={"profile_id": str(topic_service_stub.topic.profile_id)},
        )

    assert response.status_code == 200
    payload = response.json()
    assert payload["suggestions"][0]["name"] == "Ser vs Estar"
