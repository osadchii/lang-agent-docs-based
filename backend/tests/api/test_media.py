from __future__ import annotations

import io
import uuid
from collections.abc import Iterator
from datetime import datetime, timezone
from types import SimpleNamespace
from unittest.mock import AsyncMock

import pytest
import pytest_asyncio
from httpx import AsyncClient
from PIL import Image
from sqlalchemy.ext.asyncio import AsyncSession

import app.api.routes.media as media_routes
from app.api.dependencies import build_ocr_service, get_cache_client
from app.core.auth import get_current_user
from app.core.db import get_session
from app.main import app
from app.models.language_profile import LanguageProfile
from app.models.user import User
from app.schemas.llm_responses import WordSuggestion, WordSuggestions
from app.services.llm import TokenUsage
from app.services.media import OCRAnalysis, OCRSegment


def _image_file() -> tuple[str, tuple[str, bytes, str]]:
    """Create a simple in-memory PNG suitable for multipart uploads."""
    image = Image.new("RGB", (32, 32), color="white")
    buffer = io.BytesIO()
    image.save(buffer, format="PNG")
    return (
        "images",
        (
            "photo.png",
            buffer.getvalue(),
            "image/png",
        ),
    )


@pytest_asyncio.fixture()
async def user_profile(db_session: AsyncSession) -> tuple[User, LanguageProfile]:
    now = datetime.now(tz=timezone.utc)
    user = User(
        id=uuid.uuid4(),
        telegram_id=1,
        first_name="Tester",
        last_name=None,
        username=None,
        created_at=now,
        updated_at=now,
    )
    profile = LanguageProfile(
        id=uuid.uuid4(),
        user_id=user.id,
        language="es",
        language_name="Spanish",
        current_level="A2",
        target_level="B2",
        goals=["travel"],
        interface_language="ru",
        is_active=True,
        created_at=now,
        updated_at=now,
    )
    db_session.add_all([user, profile])
    await db_session.commit()
    return user, profile


_CURRENT_USER: dict[str, User | None] = {"value": None}


@pytest.fixture(autouse=True)
def override_dependencies(
    db_session: AsyncSession,
) -> Iterator[None]:
    async def _session_override() -> AsyncSession:
        yield db_session

    async def _user_override() -> User:
        assert _CURRENT_USER["value"] is not None
        return _CURRENT_USER["value"]

    app.dependency_overrides[get_session] = _session_override
    app.dependency_overrides[get_current_user] = _user_override
    yield
    app.dependency_overrides.pop(get_session, None)
    app.dependency_overrides.pop(get_current_user, None)
    app.dependency_overrides.pop(get_cache_client, None)
    app.dependency_overrides.pop(build_ocr_service, None)
    _CURRENT_USER["value"] = None


@pytest.mark.asyncio
async def test_media_ocr_returns_payload(user_profile: tuple[User, LanguageProfile]) -> None:
    user, profile = user_profile
    _CURRENT_USER["value"] = user

    analysis = OCRAnalysis(
        segments=[
            OCRSegment(
                index=0,
                full_text="Hola mundo",
                target_text="Hola",
                detected_languages=["es"],
                contains_target_language=True,
                confidence="high",
            )
        ],
        combined_text="Hola",
        has_target_language=True,
        usage=TokenUsage(0, 0, 0),
    )
    ocr_stub = SimpleNamespace(analyze=AsyncMock(return_value=analysis))
    app.dependency_overrides[build_ocr_service] = lambda: ocr_stub

    llm_stub = SimpleNamespace(
        suggest_words_from_text=AsyncMock(
            return_value=(
                WordSuggestions(
                    suggestions=[
                        WordSuggestion(word="viaje", type="noun", reason="Travel term", priority=1)
                    ]
                ),
                TokenUsage(5, 3, 8),
            )
        ),
        track_token_usage=AsyncMock(),
    )

    async def _cache_override() -> SimpleNamespace:
        return SimpleNamespace(connect=AsyncMock())

    app.dependency_overrides[get_cache_client] = _cache_override

    original_builder = media_routes.build_enhanced_llm_service
    media_routes.build_enhanced_llm_service = lambda _cache: llm_stub  # type: ignore[assignment]

    async with AsyncClient(app=app, base_url="http://testserver") as client:
        response = await client.post(
            "/api/media/ocr",
            files=[_image_file()],
            data={"profile_id": str(profile.id)},
        )

    media_routes.build_enhanced_llm_service = original_builder

    assert response.status_code == 201
    payload = response.json()
    assert payload["profile_id"] == str(profile.id)
    assert payload["combined_text"] == "Hola"
    assert payload["segments"][0]["detected_languages"] == ["es"]
    assert payload["suggestions"][0]["word"] == "viaje"


@pytest.mark.asyncio
async def test_media_ocr_uses_active_profile_when_not_specified(
    user_profile: tuple[User, LanguageProfile],
) -> None:
    user, profile = user_profile
    _CURRENT_USER["value"] = user

    analysis = OCRAnalysis(
        segments=[
            OCRSegment(
                index=0,
                full_text="Hola",
                target_text="",
                detected_languages=["es"],
                contains_target_language=False,
                confidence="low",
            )
        ],
        combined_text="Hola",
        has_target_language=False,
        usage=TokenUsage(0, 0, 0),
    )
    ocr_stub = SimpleNamespace(analyze=AsyncMock(return_value=analysis))
    app.dependency_overrides[build_ocr_service] = lambda: ocr_stub

    llm_stub = SimpleNamespace(
        suggest_words_from_text=AsyncMock(
            return_value=(WordSuggestions(suggestions=[]), TokenUsage(0, 0, 0))
        ),
        track_token_usage=AsyncMock(),
    )

    async def _cache_override() -> SimpleNamespace:
        return SimpleNamespace(connect=AsyncMock())

    app.dependency_overrides[get_cache_client] = _cache_override
    original_builder = media_routes.build_enhanced_llm_service
    media_routes.build_enhanced_llm_service = lambda _cache: llm_stub  # type: ignore[assignment]

    async with AsyncClient(app=app, base_url="http://testserver") as client:
        response = await client.post("/api/media/ocr", files=[_image_file()])

    media_routes.build_enhanced_llm_service = original_builder

    assert response.status_code == 201
    payload = response.json()
    assert payload["profile_id"] == str(profile.id)
    assert payload["has_target_language"] is False
