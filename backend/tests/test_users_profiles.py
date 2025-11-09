"""Tests for user and profile endpoints."""

from __future__ import annotations

from typing import Tuple
from uuid import UUID

from fastapi.testclient import TestClient

from app.main import app
from app.repositories.user_repository import user_repository
from tests.helpers import TEST_BOT_TOKEN, generate_init_data

client = TestClient(app)


def _authenticate() -> Tuple[dict, UUID]:
    init_data = generate_init_data(TEST_BOT_TOKEN)
    response = client.post("/api/auth/validate", json={"init_data": init_data})
    assert response.status_code == 200
    payload = response.json()
    token = payload["token"]
    user_id = UUID(payload["user"]["id"])
    headers = {"Authorization": f"Bearer {token}"}
    return headers, user_id


def test_get_user_me_returns_limits_and_subscription():
    headers, _ = _authenticate()

    response = client.get("/api/users/me", headers=headers)

    assert response.status_code == 200
    data = response.json()
    assert data["subscription"]["status"] == "free"
    assert data["limits"]["profiles"]["max"] == 1
    assert data["limits"]["profiles"]["used"] == 0


def test_patch_user_updates_name():
    headers, _ = _authenticate()

    response = client.patch("/api/users/me", headers=headers, json={"first_name": "Jane"})

    assert response.status_code == 200
    assert response.json()["first_name"] == "Jane"


def test_create_profile_success_and_list():
    headers, _ = _authenticate()

    payload = {
        "language": "es",
        "current_level": "A1",
        "target_level": "A2",
        "goals": ["travel"],
        "interface_language": "ru",
    }
    create_response = client.post("/api/profiles", headers=headers, json=payload)
    assert create_response.status_code == 201
    profile = create_response.json()
    assert profile["language"] == "es"
    assert profile["is_active"] is True

    list_response = client.get("/api/profiles", headers=headers)
    assert list_response.status_code == 200
    assert len(list_response.json()["data"]) == 1


def test_profile_duplicate_language_error():
    headers, user_id = _authenticate()
    user_repository.set_premium_status(user_id, is_premium=True)
    payload = {
        "language": "es",
        "current_level": "A1",
        "target_level": "A2",
        "goals": ["travel"],
        "interface_language": "ru",
    }
    first_response = client.post("/api/profiles", headers=headers, json=payload)
    assert first_response.status_code == 201

    duplicate_response = client.post("/api/profiles", headers=headers, json=payload)

    assert duplicate_response.status_code == 400
    assert duplicate_response.json()["detail"]["code"] == "DUPLICATE_LANGUAGE"


def test_profile_limit_for_free_plan():
    headers, _ = _authenticate()
    payload = {
        "language": "es",
        "current_level": "A1",
        "target_level": "A2",
        "goals": ["travel"],
        "interface_language": "ru",
    }
    first_response = client.post("/api/profiles", headers=headers, json=payload)
    assert first_response.status_code == 201

    second_payload = dict(payload)
    second_payload["language"] = "fr"
    limit_response = client.post("/api/profiles", headers=headers, json=second_payload)

    assert limit_response.status_code == 400
    assert limit_response.json()["detail"]["code"] == "LIMIT_REACHED"


def test_activate_profile_switches_active_state():
    headers, user_id = _authenticate()
    base_payload = {
        "language": "es",
        "current_level": "A1",
        "target_level": "A2",
        "goals": ["travel"],
        "interface_language": "ru",
    }
    first_response = client.post("/api/profiles", headers=headers, json=base_payload)
    assert first_response.status_code == 201
    first_profile = first_response.json()

    user_repository.set_premium_status(user_id, is_premium=True)
    second_payload = dict(base_payload)
    second_payload["language"] = "fr"
    second_payload["interface_language"] = "fr"
    second_response = client.post("/api/profiles", headers=headers, json=second_payload)
    assert second_response.status_code == 201
    second_profile = second_response.json()
    assert second_profile["is_active"] is False

    activate_response = client.post(f"/api/profiles/{first_profile['id']}/activate", headers=headers)

    assert activate_response.status_code == 200
    assert activate_response.json()["is_active"] is True

    list_response = client.get("/api/profiles", headers=headers).json()["data"]
    states = {profile["language"]: profile["is_active"] for profile in list_response}
    assert states["es"] is True
    assert states["fr"] is False


def test_delete_last_profile_is_not_allowed():
    headers, _ = _authenticate()
    payload = {
        "language": "es",
        "current_level": "A1",
        "target_level": "A2",
        "goals": ["travel"],
        "interface_language": "ru",
    }
    create_response = client.post("/api/profiles", headers=headers, json=payload)
    assert create_response.status_code == 201
    profile = create_response.json()

    response = client.delete(f"/api/profiles/{profile['id']}", headers=headers)
    assert response.status_code == 400
    assert response.json()["detail"]["code"] == "LAST_PROFILE"
