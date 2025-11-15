from __future__ import annotations

import uuid
from collections.abc import Iterator
from datetime import datetime, timezone
from types import SimpleNamespace
from unittest.mock import AsyncMock

import pytest
from httpx import AsyncClient

from app.api.routes.notifications import get_notification_service
from app.core.auth import get_current_user
from app.main import app
from app.services.notifications import NotificationListResult


class NotificationServiceStub:
    def __init__(self) -> None:
        self.session = SimpleNamespace(commit=AsyncMock())
        self.user = SimpleNamespace(id=uuid.uuid4())
        now = datetime.now(tz=timezone.utc)
        self.notification = SimpleNamespace(
            id=uuid.uuid4(),
            type="streak_reminder",
            title="?? ???????? ? ??????!",
            message="???????? ???? ?? ???? ???????? ???????.",
            data={"profile_id": str(uuid.uuid4()), "streak": 5},
            is_read=False,
            created_at=now,
            read_at=None,
        )
        self.notified = NotificationListResult(
            notifications=[self.notification],
            total=1,
            unread_count=1,
        )

    async def list_notifications(self, *args: object, **kwargs: object) -> NotificationListResult:
        self.last_list_kwargs = kwargs
        return self.notified

    async def mark_notification_read(
        self,
        user: object,
        notification_id: uuid.UUID,
    ) -> SimpleNamespace:
        self.notification.is_read = True
        return self.notification

    async def mark_all_notifications_read(self, user: object) -> int:
        self.notification.is_read = True
        return 1


@pytest.fixture()
def notification_service_stub() -> NotificationServiceStub:
    return NotificationServiceStub()


@pytest.fixture(autouse=True)
def _dependency_overrides(notification_service_stub: NotificationServiceStub) -> Iterator[None]:
    async def _user_override() -> SimpleNamespace:
        return notification_service_stub.user

    async def _service_override() -> NotificationServiceStub:
        return notification_service_stub

    app.dependency_overrides[get_current_user] = _user_override
    app.dependency_overrides[get_notification_service] = _service_override
    yield
    app.dependency_overrides.pop(get_current_user, None)
    app.dependency_overrides.pop(get_notification_service, None)


@pytest.mark.asyncio
async def test_list_notifications_returns_payload(
    notification_service_stub: NotificationServiceStub,
) -> None:
    async with AsyncClient(app=app, base_url="http://testserver") as client:
        response = await client.get("/api/notifications", params={"unread_only": True})

    assert response.status_code == 200
    body = response.json()
    assert body["pagination"]["count"] == 1
    assert body["unread_count"] == 1
    assert notification_service_stub.last_list_kwargs["unread_only"] is True


@pytest.mark.asyncio
async def test_mark_notification_read_returns_minimal_payload(
    notification_service_stub: NotificationServiceStub,
) -> None:
    async with AsyncClient(app=app, base_url="http://testserver") as client:
        response = await client.post(
            f"/api/notifications/{notification_service_stub.notification.id}/read"
        )

    assert response.status_code == 200
    assert response.json()["is_read"] is True
    notification_service_stub.session.commit.assert_awaited()


@pytest.mark.asyncio
async def test_mark_all_notifications_read_returns_count() -> None:
    async with AsyncClient(app=app, base_url="http://testserver") as client:
        response = await client.post("/api/notifications/read-all")

    assert response.status_code == 200
    assert response.json()["marked_read"] == 1
