from __future__ import annotations

import socket
from contextlib import asynccontextmanager
from types import MethodType, SimpleNamespace
from unittest.mock import AsyncMock, Mock

import pytest

import app.telegram.bot as telegram_bot_module
from app.services.speech_to_text import SpeechToTextResult
from app.telegram.bot import TelegramBot


class DummyApplication:
    def __init__(self) -> None:
        self.process_update = AsyncMock()
        self.initialize = AsyncMock()
        self.start = AsyncMock()
        self.stop = AsyncMock()
        self.shutdown = AsyncMock()
        self.add_handler = Mock()
        self.add_error_handler = Mock()
        self.bot = SimpleNamespace(
            set_webhook=AsyncMock(),
            delete_webhook=AsyncMock(),
        )


class RecordingMessage:
    def __init__(self, voice: SimpleNamespace | None = None) -> None:
        self.voice = voice
        self.replies: list[str] = []

    async def reply_text(self, text: str, **_: object) -> None:
        self.replies.append(text)


def build_bot(
    monkeypatch: pytest.MonkeyPatch,
    *,
    environment: str = "test",
    **bot_kwargs: object,
) -> tuple[TelegramBot, DummyApplication]:
    dummy_app = DummyApplication()

    class DummyBuilder:
        def token(self, token: str) -> "DummyBuilder":
            self.token_value = token
            return self

        def build(self) -> DummyApplication:
            return dummy_app

    monkeypatch.setattr(telegram_bot_module, "ApplicationBuilder", lambda: DummyBuilder())
    bot = TelegramBot(token="dummy-token", environment=environment, **bot_kwargs)  # noqa: S106
    return bot, dummy_app


@pytest.mark.asyncio
async def test_process_payload_dispatches_update(monkeypatch: pytest.MonkeyPatch) -> None:
    bot, dummy_app = build_bot(monkeypatch)
    payload = {"update_id": 1}
    expected_update = object()

    class DummyUpdate:
        @staticmethod
        def de_json(data: dict[str, object], bot_instance: object) -> object:
            assert data is payload
            assert bot_instance is dummy_app.bot
            return expected_update

    monkeypatch.setattr(telegram_bot_module, "Update", DummyUpdate)

    await bot.process_payload(payload)

    dummy_app.initialize.assert_awaited_once()
    dummy_app.start.assert_awaited_once()
    dummy_app.process_update.assert_awaited_once_with(expected_update)


@pytest.mark.asyncio
async def test_sync_webhook_configures_in_production(monkeypatch: pytest.MonkeyPatch) -> None:
    bot, dummy_app = build_bot(monkeypatch, environment="production")
    webhook_url = "https://api.example.com"

    monkeypatch.setattr(
        telegram_bot_module.socket,
        "getaddrinfo",
        lambda *args, **kwargs: [(None, None, None, None, None)],
    )

    await bot.sync_webhook(webhook_url)

    dummy_app.bot.set_webhook.assert_awaited_once()
    called_with = dummy_app.bot.set_webhook.await_args.kwargs
    assert called_with["url"] == f"{webhook_url}/telegram-webhook/dummy-token"
    assert called_with["drop_pending_updates"] is True


@pytest.mark.asyncio
async def test_sync_webhook_skips_for_non_production(monkeypatch: pytest.MonkeyPatch) -> None:
    bot, dummy_app = build_bot(monkeypatch, environment="test")

    await bot.sync_webhook("https://ignored.example.com")

    dummy_app.bot.set_webhook.assert_not_awaited()


@pytest.mark.asyncio
async def test_sync_webhook_skips_when_host_not_resolvable(monkeypatch: pytest.MonkeyPatch) -> None:
    bot, dummy_app = build_bot(monkeypatch, environment="production")

    def fake_getaddrinfo(host: str, *_args: object, **_kwargs: object) -> None:
        raise socket.gaierror(f"cannot resolve {host}")

    monkeypatch.setattr(telegram_bot_module.socket, "getaddrinfo", fake_getaddrinfo)

    await bot.sync_webhook("https://missing.example.com")

    dummy_app.bot.set_webhook.assert_not_awaited()


@pytest.mark.asyncio
async def test_handle_start_replies_with_greeting(monkeypatch: pytest.MonkeyPatch) -> None:
    bot, _ = build_bot(monkeypatch)

    class DummyMessage:
        def __init__(self) -> None:
            self.text: str | None = None
            self.parse_mode: str | None = None
            self.reply_markup: object | None = None

        async def reply_text(
            self, text: str, parse_mode: str | None = None, reply_markup: object | None = None
        ) -> None:
            self.text = text
            self.parse_mode = parse_mode
            self.reply_markup = reply_markup

    # Mock database session and user service
    mock_session = AsyncMock()
    mock_user = SimpleNamespace(id="test-user-id", created_at=None, updated_at=None)
    mock_service = AsyncMock()
    mock_service.get_or_create_user.return_value = mock_user

    # Mock AsyncSessionFactory context manager
    class MockSessionFactory:
        def __call__(self) -> "MockSessionFactory":
            return self

        async def __aenter__(self) -> AsyncMock:
            return mock_session

        async def __aexit__(self, *args: object) -> None:
            pass

    # Patch at the module level where it's imported
    import app.core.db as db_module

    monkeypatch.setattr(db_module, "AsyncSessionFactory", MockSessionFactory())

    # Mock repository and service constructors
    def mock_user_repository_init(session: object) -> SimpleNamespace:
        return SimpleNamespace()

    def mock_user_service_init(repo: object) -> AsyncMock:
        return mock_service

    import app.repositories.user as repo_module
    import app.services.user as service_module

    monkeypatch.setattr(repo_module, "UserRepository", mock_user_repository_init)
    monkeypatch.setattr(service_module, "UserService", mock_user_service_init)

    dummy_message = DummyMessage()
    update = SimpleNamespace(
        effective_message=dummy_message,
        effective_user=SimpleNamespace(
            id=123456,
            first_name="Антон",
            last_name="Иванов",
            username="antonivanov",
            language_code="ru",
        ),
    )

    await bot._handle_start(update, context=None)

    # Text is now formatted with Markdown, so it contains bold text
    assert "Привет, Антон" in dummy_message.text
    assert "*Привет, Антон!*" in dummy_message.text  # Check bold formatting
    assert dummy_message.parse_mode == "Markdown"
    assert dummy_message.reply_markup is not None
    mock_service.get_or_create_user.assert_awaited_once()


@pytest.mark.asyncio
async def test_handle_error_logs(
    monkeypatch: pytest.MonkeyPatch, caplog: pytest.LogCaptureFixture
) -> None:
    bot, _ = build_bot(monkeypatch)
    caplog.set_level("ERROR")
    context = SimpleNamespace(error=ValueError("boom"))

    await bot._handle_error(update={"update_id": 1}, context=context)  # type: ignore[arg-type]

    assert any("Telegram handler error" in record.message for record in caplog.records)


@pytest.mark.asyncio
async def test_handle_voice_message_rejects_when_too_long(monkeypatch: pytest.MonkeyPatch) -> None:
    speech_service = SimpleNamespace(transcribe=AsyncMock())
    bot, _ = build_bot(monkeypatch, speech_to_text_service=speech_service)
    bot._max_voice_duration_seconds = 5
    voice = SimpleNamespace(duration=10, file_id="file", file_size=1024)
    message = RecordingMessage(voice=voice)
    update = SimpleNamespace(effective_message=message, effective_user=SimpleNamespace(id=1))

    await bot._handle_voice_message(update, context=SimpleNamespace(bot=SimpleNamespace()))

    assert message.replies[0].startswith("⚠️ Голосовое сообщение слишком длинное")
    speech_service.transcribe.assert_not_called()


@pytest.mark.asyncio
async def test_handle_voice_message_rejects_when_file_too_large(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    speech_service = SimpleNamespace(transcribe=AsyncMock())
    bot, _ = build_bot(monkeypatch, speech_to_text_service=speech_service)
    bot._max_voice_file_size_bytes = 10
    voice = SimpleNamespace(duration=2, file_id="file", file_size=20)
    message = RecordingMessage(voice=voice)
    update = SimpleNamespace(effective_message=message, effective_user=SimpleNamespace(id=1))

    await bot._handle_voice_message(update, context=SimpleNamespace(bot=SimpleNamespace()))

    assert "слишком большое" in message.replies[0]
    speech_service.transcribe.assert_not_called()


@pytest.mark.asyncio
async def test_handle_voice_message_processes_transcript(monkeypatch: pytest.MonkeyPatch) -> None:
    speech_service = SimpleNamespace(
        transcribe=AsyncMock(
            return_value=SpeechToTextResult(text=" Привет мир ", detected_language="es")
        )
    )
    bot, _ = build_bot(monkeypatch, speech_to_text_service=speech_service)

    voice = SimpleNamespace(duration=2, file_id="voice", file_size=2000)
    message = RecordingMessage(voice=voice)
    user = SimpleNamespace(
        id=99,
        first_name="Tester",
        last_name=None,
        username=None,
        language_code="ru",
    )
    update = SimpleNamespace(effective_message=message, effective_user=user)

    file_obj = SimpleNamespace(download_as_bytearray=AsyncMock(return_value=b"voice-bytes"))
    bot_file = SimpleNamespace(get_file=AsyncMock(return_value=file_obj))
    context = SimpleNamespace(bot=bot_file)

    dialog_response = "Ответ"
    process_mock = AsyncMock(return_value=dialog_response)
    dialog_context = SimpleNamespace(
        user=SimpleNamespace(id="user-id"),
        profile=SimpleNamespace(id="profile-id", language="es"),
        dialog_service=SimpleNamespace(process_message=process_mock),
    )

    @asynccontextmanager
    async def fake_context() -> SimpleNamespace:
        yield dialog_context

    def fake_dialog_context(self: TelegramBot, *, telegram_user: object) -> object:
        assert telegram_user is user
        return fake_context()

    bot._dialog_context = MethodType(fake_dialog_context, bot)
    bot._send_dialog_response = AsyncMock()

    await bot._handle_voice_message(update, context=context)

    speech_service.transcribe.assert_awaited_once()
    assert (
        speech_service.transcribe.await_args.kwargs["language_hint"]
        == dialog_context.profile.language
    )
    bot_file.get_file.assert_awaited_once_with("voice")
    file_obj.download_as_bytearray.assert_awaited_once()
    process_mock.assert_awaited_once_with(
        user=dialog_context.user,
        profile_id=dialog_context.profile.id,
        message="Привет мир",
    )
    bot._send_dialog_response.assert_awaited_once_with(message, dialog_response)
    assert message.replies == []
