from __future__ import annotations

import io
import json
from types import SimpleNamespace
from unittest.mock import AsyncMock

import pytest
from PIL import Image

from app.core.errors import ApplicationError
from app.services.media import ImageInput, OCRService


def _image_bytes(size: int = 64) -> bytes:
    """Generate a simple in-memory PNG."""
    image = Image.new("RGB", (size, size), color="white")
    buffer = io.BytesIO()
    image.save(buffer, format="PNG")
    return buffer.getvalue()


def _vision_response(content: str) -> SimpleNamespace:
    usage = SimpleNamespace(prompt_tokens=5, completion_tokens=3, total_tokens=8)
    message = SimpleNamespace(content=content)
    choice = SimpleNamespace(message=message)
    return SimpleNamespace(choices=[choice], usage=usage)


@pytest.mark.asyncio
async def test_analyze_returns_segments() -> None:
    response_payload = json.dumps(
        {
            "full_text": "Hola mundo",
            "target_text": "Hola",
            "detected_languages": ["es"],
            "contains_target_language": True,
        }
    )
    mock_client = SimpleNamespace(
        chat=SimpleNamespace(
            completions=SimpleNamespace(
                create=AsyncMock(return_value=_vision_response(response_payload))
            )
        )
    )
    service = OCRService(
        api_key="test",
        client=mock_client,
        max_images=2,
        max_image_bytes=200_000,
        max_image_dimension=256,
    )

    inputs = [
        ImageInput(name="photo.png", content_type="image/png", data=_image_bytes()),
    ]

    analysis = await service.analyze(
        inputs,
        target_language_code="es",
        target_language_name="Spanish",
    )

    assert analysis.combined_text == "Hola"
    assert analysis.has_target_language is True
    assert analysis.segments[0].detected_languages == ["es"]
    mock_client.chat.completions.create.assert_awaited_once()


@pytest.mark.asyncio
async def test_analyze_rejects_too_many_images() -> None:
    service = OCRService(api_key="test", max_images=1)
    with pytest.raises(ApplicationError):
        await service.analyze(
            [
                ImageInput(name="1.png", content_type="image/png", data=_image_bytes()),
                ImageInput(name="2.png", content_type="image/png", data=_image_bytes()),
            ],
            target_language_code="es",
            target_language_name="Spanish",
        )


@pytest.mark.asyncio
async def test_analyze_uses_full_text_when_target_missing() -> None:
    response_payload = json.dumps(
        {
            "full_text": "Bonjour",
            "target_text": "",
            "detected_languages": ["fr"],
            "contains_target_language": False,
        }
    )
    mock_client = SimpleNamespace(
        chat=SimpleNamespace(
            completions=SimpleNamespace(
                create=AsyncMock(return_value=_vision_response(response_payload))
            )
        )
    )
    service = OCRService(api_key="test", client=mock_client)

    analysis = await service.analyze(
        [ImageInput(name="photo.png", content_type="image/png", data=_image_bytes())],
        target_language_code="es",
        target_language_name="Spanish",
    )

    assert analysis.combined_text == "Bonjour"
    assert analysis.has_target_language is False


@pytest.mark.asyncio
async def test_analyze_supports_list_payloads_from_vision() -> None:
    response_payload = json.dumps(
        {
            "full_text": ["Linea 1", "Linea 2"],
            "target_text": ["Hola", "Mundo"],
            "detected_languages": ["es"],
            "contains_target_language": True,
        }
    )
    mock_client = SimpleNamespace(
        chat=SimpleNamespace(
            completions=SimpleNamespace(
                create=AsyncMock(return_value=_vision_response(response_payload))
            )
        )
    )
    service = OCRService(api_key="test", client=mock_client)

    analysis = await service.analyze(
        [ImageInput(name="photo.png", content_type="image/png", data=_image_bytes())],
        target_language_code="es",
        target_language_name="Spanish",
    )

    assert analysis.segments[0].target_text == "Hola Mundo"
