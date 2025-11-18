from __future__ import annotations

import uuid
from collections.abc import Generator
from datetime import datetime, timezone
from types import SimpleNamespace
from unittest.mock import AsyncMock

import pytest
from httpx import AsyncClient

from app.api.routes.admin import get_admin_service
from app.core.auth import get_current_user, require_admin
from app.main import app
from app.schemas.admin import AdminMetricsPeriod
from app.services.admin import (
    AdminMetricsActivityBlock,
    AdminMetricsContentBlock,
    AdminMetricsResult,
    AdminMetricsRetentionBlock,
    AdminMetricsRevenueBlock,
    AdminMetricsUsersBlock,
    AdminUserListResult,
    AdminUserView,
    ManualPremiumGrant,
)


class StubAdminService:
    """Test double providing deterministic responses."""

    def __init__(self) -> None:
        now = datetime.now(tz=timezone.utc)
        self.user_view = AdminUserView(
            id=uuid.uuid4(),
            telegram_id=123,
            first_name="Test",
            last_name=None,
            username="tester",
            is_premium=True,
            languages=["es"],
            cards_count=42,
            exercises_count=3,
            streak=7,
            last_activity=now,
            created_at=now,
        )
        self.session = SimpleNamespace(commit=AsyncMock())

    async def list_users(self, **params: object) -> AdminUserListResult:
        self.list_call = params
        params.setdefault("limit", 50)
        params.setdefault("offset", 0)
        return AdminUserListResult(
            users=[self.user_view],
            total=1,
            limit=params["limit"],
            offset=params["offset"],
        )

    async def get_metrics(self, period: AdminMetricsPeriod) -> AdminMetricsResult:
        self.metrics_period = period
        users = AdminMetricsUsersBlock(
            total=10, new=2, active=5, premium=3, premium_percentage=30.0
        )
        retention = AdminMetricsRetentionBlock(day_7=0.5, day_30=0.3)
        content = AdminMetricsContentBlock(total_cards=200, total_exercises=40, total_groups=5)
        activity = AdminMetricsActivityBlock(
            messages_sent=100,
            cards_studied=50,
            exercises_completed=25,
            average_session_minutes=12.5,
        )
        revenue = AdminMetricsRevenueBlock(total="0.00", currency="EUR", subscriptions_active=3)
        return AdminMetricsResult(
            period=period,
            users=users,
            retention=retention,
            content=content,
            activity=activity,
            revenue=revenue,
        )

    async def grant_manual_premium(self, **params: object) -> ManualPremiumGrant:
        self.grant_call = params
        return ManualPremiumGrant(
            user_id=params["user_id"],
            is_premium=True,
            expires_at=datetime.now(tz=timezone.utc),
            reason=params.get("reason"),
        )


@pytest.fixture()
def stub_admin_service() -> StubAdminService:
    return StubAdminService()


@pytest.fixture()
def admin_user() -> SimpleNamespace:
    return SimpleNamespace(id=uuid.uuid4(), is_admin=True)


@pytest.fixture()
def override_dependencies(
    stub_admin_service: StubAdminService, admin_user: SimpleNamespace
) -> Generator[None, None, None]:
    async def _admin_dep() -> SimpleNamespace:
        return admin_user

    async def _service_dep() -> StubAdminService:
        return stub_admin_service

    app.dependency_overrides[require_admin] = _admin_dep
    app.dependency_overrides[get_admin_service] = _service_dep
    yield
    app.dependency_overrides.pop(require_admin, None)
    app.dependency_overrides.pop(get_admin_service, None)


@pytest.mark.asyncio
async def test_admin_users_endpoint_returns_payload(
    stub_admin_service: StubAdminService,
    override_dependencies: None,
) -> None:
    params = {
        "status": "premium",
        "activity": "active_7d",
        "language": "es",
        "sort": "cards_count",
        "limit": 25,
        "offset": 10,
    }
    async with AsyncClient(app=app, base_url="http://testserver") as client:
        response = await client.get("/api/admin/users", params=params)

    assert response.status_code == 200
    payload = response.json()
    assert payload["data"][0]["id"] == str(stub_admin_service.user_view.id)
    assert payload["pagination"]["count"] == 1
    assert stub_admin_service.list_call["status"].value == "premium"
    assert stub_admin_service.list_call["language"] == "es"


@pytest.mark.asyncio
async def test_admin_metrics_endpoint_returns_snapshot(
    stub_admin_service: StubAdminService,
    override_dependencies: None,
) -> None:
    async with AsyncClient(app=app, base_url="http://testserver") as client:
        response = await client.get("/api/admin/metrics", params={"period": "7d"})

    assert response.status_code == 200
    body = response.json()
    assert body["period"] == "7d"
    assert body["users"]["premium"] == 3
    assert stub_admin_service.metrics_period == AdminMetricsPeriod.DAYS_7


@pytest.mark.asyncio
async def test_manual_premium_endpoint_commits_transaction(
    stub_admin_service: StubAdminService,
    override_dependencies: None,
) -> None:
    target_user_id = uuid.uuid4()
    async with AsyncClient(app=app, base_url="http://testserver") as client:
        response = await client.post(
            f"/api/admin/users/{target_user_id}/premium",
            json={"duration_days": 30, "reason": "Gift"},
        )

    assert response.status_code == 200
    assert stub_admin_service.grant_call["user_id"] == target_user_id
    assert stub_admin_service.session.commit.await_count == 1


@pytest.mark.asyncio
async def test_admin_routes_require_admin(stub_admin_service: StubAdminService) -> None:
    async def _non_admin() -> SimpleNamespace:
        return SimpleNamespace(is_admin=False)

    async def _service_override() -> StubAdminService:
        return stub_admin_service

    app.dependency_overrides[get_current_user] = _non_admin
    app.dependency_overrides[get_admin_service] = _service_override

    try:
        async with AsyncClient(app=app, base_url="http://testserver") as client:
            response = await client.get("/api/admin/users")
        assert response.status_code == 403
    finally:
        app.dependency_overrides.pop(get_current_user, None)
        app.dependency_overrides.pop(get_admin_service, None)
