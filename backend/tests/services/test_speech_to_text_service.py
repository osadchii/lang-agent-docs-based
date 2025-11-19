from __future__ import annotations

from types import SimpleNamespace
from typing import cast
from unittest.mock import AsyncMock

import httpx
import pytest
from openai import AsyncOpenAI, BadRequestError

from app.services.speech_to_text import (
    SpeechToTextResult,
    SpeechToTextService,
    _build_openai_error_context,
    _summarize_openai_error_context,
)


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
async def test_transcribe_normalizes_language_aliases() -> None:
    create_mock = AsyncMock()
    create_mock.return_value = SimpleNamespace(text="ok", language="el")
    mock_client = cast(
        AsyncOpenAI,
        SimpleNamespace(audio=SimpleNamespace(transcriptions=SimpleNamespace(create=create_mock))),
    )

    service = SpeechToTextService(api_key="test-key", client=mock_client)

    await service.transcribe(b"voice", language_hint="gr")

    assert create_mock.await_args is not None
    assert create_mock.await_args.kwargs["language"] == "el"


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


def test_build_openai_error_context_includes_response_details() -> None:
    request = httpx.Request("POST", "https://api.openai.com/v1/audio/transcriptions")
    response = httpx.Response(
        status_code=400,
        request=request,
        json={"error": {"message": "Invalid audio file", "code": "file_invalid", "param": "file"}},
        headers={"x-request-id": "req_123456"},
    )
    body = response.json()
    error = BadRequestError("Invalid audio file", response=response, body=body)

    context = _build_openai_error_context(error)

    assert context["status_code"] == 400
    assert context["openai_code"] == "file_invalid"
    assert context["openai_param"] == "file"
    assert context["response_body"] == body
    assert context["request_id"] == "req_123456"


def test_summarize_openai_error_context_truncates_large_payload() -> None:
    context = {
        "status_code": 400,
        "openai_code": "file_invalid",
        "response_body": {"error": {"message": "A" * 1000}},
        "request_id": "req_truncate",
    }

    summary = _summarize_openai_error_context(context, max_response_chars=100)

    assert "status_code=400" in summary
    assert "openai_code=file_invalid" in summary
    assert "request_id=req_truncate" in summary
    body_fragment = next(part for part in summary.split(", ") if part.startswith("response_body="))
    assert body_fragment.endswith("...")
