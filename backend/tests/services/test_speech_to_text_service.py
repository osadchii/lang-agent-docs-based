from __future__ import annotations

from types import SimpleNamespace
from typing import cast
from unittest.mock import AsyncMock

import pytest
from openai import AsyncOpenAI

from app.services.speech_to_text import SpeechToTextResult, SpeechToTextService


@pytest.mark.asyncio
async def test_transcribe_returns_normalized_result() -> None:
    create_mock = AsyncMock()
    create_mock.return_value = SimpleNamespace(text=" hello ", language="en")
    mock_client = cast(
        AsyncOpenAI,
        SimpleNamespace(audio=SimpleNamespace(transcriptions=SimpleNamespace(create=create_mock))),
    )

    service = SpeechToTextService(api_key="test-key", client=mock_client, model="whisper-2")

    result = await service.transcribe(b"voice-bytes", language_hint="es")

    assert isinstance(result, SpeechToTextResult)
    assert result.text == "hello"
    assert result.detected_language == "en"

    assert create_mock.await_args is not None
    called_with = create_mock.await_args.kwargs
    assert called_with["language"] == "es"
    assert called_with["model"] == "whisper-2"


@pytest.mark.asyncio
async def test_transcribe_rejects_empty_payload() -> None:
    mock_client = cast(
        AsyncOpenAI,
        SimpleNamespace(audio=SimpleNamespace(transcriptions=SimpleNamespace(create=AsyncMock()))),
    )

    service = SpeechToTextService(
        api_key="test-key",
        client=mock_client,
    )

    with pytest.raises(ValueError):
        await service.transcribe(b"")
