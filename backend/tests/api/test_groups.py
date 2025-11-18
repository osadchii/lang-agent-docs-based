from __future__ import annotations

import uuid
from datetime import datetime, timezone
from types import SimpleNamespace

import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.routes.groups import get_group_service
from app.core.auth import get_current_user
from app.main import app
from app.models.group import GroupMaterialType, GroupRole
from app.services.group import GroupListItem, GroupService, MemberInfo, SharedMaterial


class GroupServiceStub:
    def __init__(self) -> None:
        now = datetime.now(tz=timezone.utc)
        self.owner_user = SimpleNamespace(
            id=uuid.uuid4(),
            telegram_id=101,
            username="sensei",
            first_name="Sensei",
            last_name=None,
        )
        self.member_user = SimpleNamespace(
            id=uuid.uuid4(),
            telegram_id=202,
            username="learner",
            first_name="Learner",
            last_name=None,
        )
        self.group = SimpleNamespace(
            id=uuid.uuid4(),
            owner_id=self.owner_user.id,
            owner=self.owner_user,
            name="Study circle",
            description=None,
            members_count=2,
            max_members=5,
            created_at=now,
            updated_at=now,
        )
        self.shared_materials = [
            SharedMaterial(
                id=uuid.uuid4(),
                type=GroupMaterialType.DECK,
                name="Deck Basics",
                description=None,
                owner_id=self.group.owner_id,
                owner_name="sensei",
                cards_count=20,
                exercises_count=None,
                shared_at=now,
            )
        ]
        self.members = [
            MemberInfo(user=self.owner_user, role=GroupRole.OWNER, joined_at=now),
            MemberInfo(user=self.member_user, role=GroupRole.MEMBER, joined_at=now),
        ]
        self.invite = SimpleNamespace(
            id=uuid.uuid4(),
            group_id=self.group.id,
            invitee_id=self.member_user.id,
            invitee=self.member_user,
            status="pending",
            created_at=now,
            expires_at=now,
        )

    async def list_groups(self, *args: object, **kwargs: object) -> list[GroupListItem]:
        return [
            GroupListItem(
                group=self.group, role=GroupRole.OWNER, materials_count=len(self.shared_materials)
            )
        ]

    async def create_group(self, *args: object, **kwargs: object) -> SimpleNamespace:
        return self.group

    async def invite_member(self, *args: object, **kwargs: object) -> SimpleNamespace:
        return self.invite

    async def add_materials(self, *args: object, **kwargs: object) -> SimpleNamespace:
        entry = SimpleNamespace(
            id=uuid.uuid4(),
            type=GroupMaterialType.DECK,
            name="Deck Basics",
            reason=None,
        )
        return SimpleNamespace(added=[entry], already_shared=[], failed=[])

    async def list_materials(self, *args: object, **kwargs: object) -> list[SharedMaterial]:
        return self.shared_materials

    async def get_group(self, *args: object, **kwargs: object) -> tuple[SimpleNamespace, GroupRole]:
        return self.group, GroupRole.OWNER

    async def update_group(self, *args: object, **kwargs: object) -> SimpleNamespace:
        self.group.name = "Updated"
        return self.group

    async def delete_group(self, *args: object, **kwargs: object) -> None:
        self.deleted_group = True

    async def list_members(self, *args: object, **kwargs: object) -> list[MemberInfo]:
        return self.members

    async def remove_member(self, *args: object, **kwargs: object) -> None:
        self.removed_member = True

    async def leave_group(self, *args: object, **kwargs: object) -> None:
        self.left_group = True

    async def list_invites(self, *args: object, **kwargs: object) -> list[SimpleNamespace]:
        return [self.invite]

    async def cancel_invite(self, *args: object, **kwargs: object) -> None:
        self.invite.status = "cancelled"

    async def accept_invite(self, *args: object, **kwargs: object) -> SimpleNamespace:
        return SimpleNamespace(
            group_id=self.group.id,
            group_name=self.group.name,
            role=GroupRole.MEMBER,
            joined_at=datetime.now(tz=timezone.utc),
        )

    async def decline_invite(self, *args: object, **kwargs: object) -> None:
        self.invite.status = "declined"

    async def remove_material(self, *args: object, **kwargs: object) -> None:
        self.shared_materials.clear()

    async def count_materials(self, *args: object, **kwargs: object) -> dict[uuid.UUID, int]:
        return {self.group.id: len(self.shared_materials)}


@pytest.fixture()
def stub_user() -> SimpleNamespace:
    return SimpleNamespace(id=uuid.uuid4(), username="owner")


@pytest.fixture()
def group_service_stub() -> GroupServiceStub:
    return GroupServiceStub()


@pytest.fixture(autouse=True)
def _overrides(
    stub_user: SimpleNamespace,
    group_service_stub: GroupServiceStub,
) -> None:
    async def _user_override() -> SimpleNamespace:
        return stub_user

    async def _service_override() -> GroupServiceStub:
        return group_service_stub

    app.dependency_overrides[get_current_user] = _user_override
    app.dependency_overrides[get_group_service] = _service_override
    yield
    app.dependency_overrides.pop(get_current_user, None)
    app.dependency_overrides.pop(get_group_service, None)


@pytest.mark.asyncio
async def test_list_groups_returns_payload() -> None:
    async with AsyncClient(app=app, base_url="http://testserver") as client:
        response = await client.get("/api/groups")

    assert response.status_code == 200
    data = response.json()["data"][0]
    assert data["name"] == "Study circle"
    assert data["owner_name"] == "sensei"
    assert data["materials_count"] == 1


@pytest.mark.asyncio
async def test_create_group_returns_serialized_group(group_service_stub: GroupServiceStub) -> None:
    async with AsyncClient(app=app, base_url="http://testserver") as client:
        response = await client.post(
            "/api/groups",
            json={"name": "Anything", "description": "Ignored by stub"},
        )

    assert response.status_code == 201
    payload = response.json()
    assert payload["id"] == str(group_service_stub.group.id)
    assert payload["materials_count"] == 0


@pytest.mark.asyncio
async def test_invite_member_returns_metadata(group_service_stub: GroupServiceStub) -> None:
    async with AsyncClient(app=app, base_url="http://testserver") as client:
        response = await client.post(
            f"/api/groups/{group_service_stub.group.id}/members",
            json={"user_identifier": "@learner"},
        )

    assert response.status_code == 201
    payload = response.json()
    assert payload["user_name"] == "learner"
    assert payload["status"] == "pending"


@pytest.mark.asyncio
async def test_add_materials_returns_batch() -> None:
    async with AsyncClient(app=app, base_url="http://testserver") as client:
        response = await client.post(
            "/api/groups/00000000-0000-0000-0000-000000000000/materials",
            json={
                "material_ids": [str(uuid.uuid4())],
                "type": "deck",
            },
        )

    assert response.status_code == 201
    payload = response.json()
    assert payload["added"][0]["type"] == "deck"


@pytest.mark.asyncio
async def test_list_materials_returns_shared_materials() -> None:
    async with AsyncClient(app=app, base_url="http://testserver") as client:
        response = await client.get("/api/groups/00000000-0000-0000-0000-000000000000/materials")

    assert response.status_code == 200
    payload = response.json()["data"][0]
    assert payload["name"] == "Deck Basics"
    assert payload["type"] == "deck"


@pytest.mark.asyncio
async def test_get_and_update_group_endpoints(group_service_stub: GroupServiceStub) -> None:
    group_id = group_service_stub.group.id
    async with AsyncClient(app=app, base_url="http://testserver") as client:
        detail = await client.get(f"/api/groups/{group_id}")
        assert detail.status_code == 200
        updated = await client.patch(f"/api/groups/{group_id}", json={"name": "Updated"})
        assert updated.status_code == 200
        assert updated.json()["name"] == "Updated"
        delete_response = await client.delete(f"/api/groups/{group_id}")
        assert delete_response.status_code == 204


@pytest.mark.asyncio
async def test_members_and_leave_routes(group_service_stub: GroupServiceStub) -> None:
    group_id = group_service_stub.group.id
    member_id = group_service_stub.member_user.id
    async with AsyncClient(app=app, base_url="http://testserver") as client:
        members = await client.get(f"/api/groups/{group_id}/members")
        assert members.status_code == 200
        removed = await client.delete(f"/api/groups/{group_id}/members/{member_id}")
        assert removed.status_code == 204
        left = await client.post(f"/api/groups/{group_id}/leave")
        assert left.status_code == 204


@pytest.mark.asyncio
async def test_invite_management_routes(group_service_stub: GroupServiceStub) -> None:
    group_id = group_service_stub.group.id
    invite_id = group_service_stub.invite.id
    async with AsyncClient(app=app, base_url="http://testserver") as client:
        invites = await client.get(f"/api/groups/{group_id}/invites")
        assert invites.status_code == 200
        cancel = await client.delete(f"/api/groups/invites/{invite_id}")
        assert cancel.status_code == 204
        accept = await client.post(f"/api/groups/invites/{invite_id}/accept")
        assert accept.status_code == 200
        decline = await client.post(f"/api/groups/invites/{invite_id}/decline")
        assert decline.status_code == 204


@pytest.mark.asyncio
async def test_remove_member_and_material_routes(group_service_stub: GroupServiceStub) -> None:
    group_id = group_service_stub.group.id
    material_id = group_service_stub.shared_materials[0].id
    async with AsyncClient(app=app, base_url="http://testserver") as client:
        delete_material = await client.delete(
            f"/api/groups/{group_id}/materials/{material_id}",
            params={"material_type": "deck"},
        )
        assert delete_material.status_code == 204


@pytest.mark.asyncio
async def test_get_group_service_wires_repositories(db_session: AsyncSession) -> None:
    service = await get_group_service(db_session)

    assert isinstance(service, GroupService)
    assert service.group_repo.session is db_session
