from __future__ import annotations

import uuid
from datetime import datetime, timedelta, timezone
from types import SimpleNamespace
from unittest.mock import AsyncMock

import pytest
from httpx import AsyncClient

from app.api.routes.dialog import get_dialog_service
from app.core.auth import get_current_user
from app.core.errors import ApplicationError, ErrorCode
from app.main import app
from app.models.conversation import MessageRole


class StubDialogService:
    """Test double for DialogService allowing custom history fixtures."""

    def __init__(self) -> None:
        self.profile = SimpleNamespace(id=uuid.uuid4())
        self._next_error: Exception | None = None
        session_mock = SimpleNamespace()
        session_mock.execute = AsyncMock(
            return_value=SimpleNamespace(scalar_one_or_none=lambda: self.profile)
        )

        self.conversation_repo = SimpleNamespace(
            session=session_mock,
            get_recent_for_profile=AsyncMock(return_value=[]),
        )

    async def get_or_create_default_profile(
        self, *args: object, **kwargs: object
    ) -> SimpleNamespace:
        return self.profile

    async def process_message(self, **kwargs: object) -> str:
        self.last_payload = kwargs
        if self._next_error is not None:
            error = self._next_error
            self._next_error = None
            raise error
        return "Привет! Чем могу помочь?"

    def set_history(self, messages: list[SimpleNamespace]) -> None:
        self.conversation_repo.get_recent_for_profile = AsyncMock(return_value=messages)

    def set_profile_lookup(self, profile: SimpleNamespace | None) -> None:
        self.conversation_repo.session.execute = AsyncMock(
            return_value=SimpleNamespace(scalar_one_or_none=lambda: profile)
        )

    def set_next_error(self, error: Exception) -> None:
        self._next_error = error


def _message(*, role: MessageRole, content: str, minutes_ago: int = 0) -> SimpleNamespace:
    timestamp = datetime.now(tz=timezone.utc) - timedelta(minutes=minutes_ago)
    return SimpleNamespace(
        id=uuid.uuid4(),
        profile_id=uuid.uuid4(),
        role=role,
        content=content,
        timestamp=timestamp,
    )


@pytest.fixture()
def stub_user() -> SimpleNamespace:
    return SimpleNamespace(id=uuid.uuid4(), language_code="ru")


@pytest.fixture()
def dialog_stub() -> StubDialogService:
    return StubDialogService()


@pytest.fixture(autouse=True)
def override_dependencies(stub_user: SimpleNamespace, dialog_stub: StubDialogService) -> None:
    async def _user_override() -> SimpleNamespace:
        return stub_user

    async def _dialog_override() -> StubDialogService:
        return dialog_stub

    app.dependency_overrides[get_current_user] = _user_override
    app.dependency_overrides[get_dialog_service] = _dialog_override

    yield

    app.dependency_overrides.pop(get_current_user, None)
    app.dependency_overrides.pop(get_dialog_service, None)


@pytest.mark.asyncio
async def test_chat_endpoint_returns_assistant_message(
    dialog_stub: StubDialogService,
) -> None:
    assistant_msg = SimpleNamespace(
        id=uuid.uuid4(),
        profile_id=dialog_stub.profile.id,
        role=MessageRole.ASSISTANT,
        content="AI ответ",
        timestamp=datetime.now(tz=timezone.utc),
    )
    dialog_stub.set_history([assistant_msg])

    async with AsyncClient(app=app, base_url="http://testserver") as client:
        response = await client.post("/api/sessions/chat", json={"message": "Hello"})

    assert response.status_code == 201
    payload = response.json()
    assert payload["message"]["content"] == "AI ответ"
    assert payload["message"]["role"] == "assistant"


@pytest.mark.asyncio
async def test_history_endpoint_orders_messages_chronologically(
    dialog_stub: StubDialogService,
) -> None:
    newer = SimpleNamespace(
        id=uuid.uuid4(),
        profile_id=dialog_stub.profile.id,
        role=MessageRole.ASSISTANT,
        content="Последний ответ",
        timestamp=datetime.now(tz=timezone.utc),
    )
    older = SimpleNamespace(
        id=uuid.uuid4(),
        profile_id=dialog_stub.profile.id,
        role=MessageRole.USER,
        content="Старый вопрос",
        timestamp=datetime.now(tz=timezone.utc) - timedelta(minutes=5),
    )
    dialog_stub.set_history([newer, older])

    async with AsyncClient(app=app, base_url="http://testserver") as client:
        response = await client.get("/api/dialog/history", params={"limit": 1})

    assert response.status_code == 200
    payload = response.json()
    assert payload["messages"][0]["content"] == "Последний ответ"
    assert payload["pagination"]["has_more"] is True
    assert payload["pagination"]["next_offset"] == 1


@pytest.mark.asyncio
async def test_chat_endpoint_rejects_unknown_profile(
    dialog_stub: StubDialogService,
) -> None:
    dialog_stub.set_profile_lookup(None)

    async with AsyncClient(app=app, base_url="http://testserver") as client:
        response = await client.post(
            "/api/sessions/chat",
            json={
                "message": "Hello",
                "profile_id": str(uuid.uuid4()),
            },
        )

    assert response.status_code == 404
    payload = response.json()
    assert payload["error"]["code"] == "PROFILE_NOT_FOUND"


@pytest.mark.asyncio
async def test_chat_endpoint_surfaces_application_error(
    dialog_stub: StubDialogService,
) -> None:
    dialog_stub.set_next_error(
        ApplicationError(
            code=ErrorCode.CONTENT_REJECTED,
            message="Blocked",
            details={"reason": "spam"},
        )
    )

    async with AsyncClient(app=app, base_url="http://testserver") as client:
        response = await client.post("/api/sessions/chat", json={"message": "Hello"})

    assert response.status_code == 400
    payload = response.json()
    assert payload["error"]["code"] == "CONTENT_REJECTED"
    assert payload["error"]["message"] == "Blocked"
