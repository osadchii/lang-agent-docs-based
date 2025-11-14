from __future__ import annotations

import uuid
from datetime import datetime, timezone
from types import SimpleNamespace
from unittest.mock import AsyncMock

import pytest
from httpx import AsyncClient

from app.api.routes.exercises import get_exercise_service
from app.core.auth import get_current_user
from app.main import app
from app.models.exercise import ExerciseResultType, ExerciseType


class ExerciseServiceStub:
    def __init__(self) -> None:
        self.session = SimpleNamespace(commit=AsyncMock())
        self.exercise_id = uuid.uuid4()
        self.topic_id = uuid.uuid4()

    async def generate_exercise(self, user: object, payload: object) -> SimpleNamespace:
        self.generated_payload = payload
        return SimpleNamespace(
            id=self.exercise_id,
            topic_id=self.topic_id,
            type=ExerciseType.FREE_TEXT,
            question="?????????? ?? ?????????:",
            prompt="Yo ____ en Madrid dos a�os",
            hint="???????? ??????????? ???????",
            options=None,
            correct_index=None,
            metadata={"difficulty": "medium"},
        )

    async def submit_answer(
        self,
        user: object,
        exercise_id: uuid.UUID,
        payload: object,
    ) -> SimpleNamespace:
        self.submitted = payload
        return SimpleNamespace(
            result=ExerciseResultType.CORRECT,
            correct_answer="He vivido",
            explanation="???????? Pret�rito Perfecto",
            alternatives=["He residido"],
            feedback="???????!",
            mistakes=[],
        )

    async def get_hint(self, user: object, exercise_id: uuid.UUID) -> str:
        self.hint_request = exercise_id
        return "?????????, ??????? ?? ???????? ? ????????? Pret�rito Perfecto"

    async def list_history(
        self,
        user: object,
        *,
        profile_id: uuid.UUID | None,
        topic_id: uuid.UUID | None,
        limit: int,
        offset: int,
    ) -> tuple[list[SimpleNamespace], int]:
        now = datetime.now(tz=timezone.utc)
        entry = SimpleNamespace(
            id=uuid.uuid4(),
            topic_id=self.topic_id,
            topic=SimpleNamespace(name="Pret�rito Perfecto"),
            type=ExerciseType.FREE_TEXT,
            question="?????",
            prompt="Prompt",
            user_answer="Respuesta",
            result=ExerciseResultType.CORRECT,
            used_hint=False,
            duration_seconds=42,
            completed_at=now,
        )
        return [entry], 1


@pytest.fixture()
def stub_user() -> SimpleNamespace:
    return SimpleNamespace(id=uuid.uuid4())


@pytest.fixture()
def exercise_service_stub() -> ExerciseServiceStub:
    return ExerciseServiceStub()


@pytest.fixture(autouse=True)
def _overrides(stub_user: SimpleNamespace, exercise_service_stub: ExerciseServiceStub) -> None:
    async def _user_override() -> SimpleNamespace:
        return stub_user

    async def _service_override() -> ExerciseServiceStub:
        return exercise_service_stub

    app.dependency_overrides[get_current_user] = _user_override
    app.dependency_overrides[get_exercise_service] = _service_override
    yield
    app.dependency_overrides.pop(get_current_user, None)
    app.dependency_overrides.pop(get_exercise_service, None)


@pytest.mark.asyncio
async def test_generate_exercise_returns_payload() -> None:
    async with AsyncClient(app=app, base_url="http://testserver") as client:
        response = await client.post(
            "/api/exercises/generate",
            json={"topic_id": str(uuid.uuid4()), "type": "free_text"},
        )

    assert response.status_code == 200
    payload = response.json()
    assert payload["metadata"]["difficulty"] == "medium"
    assert payload["question"].startswith("??????????")


@pytest.mark.asyncio
async def test_submit_exercise_returns_result() -> None:
    async with AsyncClient(app=app, base_url="http://testserver") as client:
        response = await client.post(
            f"/api/exercises/{uuid.uuid4()}/submit",
            json={"answer": "He vivido en Madrid", "used_hint": False},
        )

    assert response.status_code == 200
    assert response.json()["result"] == "correct"


@pytest.mark.asyncio
async def test_history_endpoint_returns_entries() -> None:
    async with AsyncClient(app=app, base_url="http://testserver") as client:
        response = await client.get("/api/exercises/history")

    assert response.status_code == 200
    payload = response.json()
    assert payload["data"][0]["topic_name"] == "Pret�rito Perfecto"
    assert payload["pagination"]["count"] == 1
