from __future__ import annotations

import socket
from types import SimpleNamespace
from unittest.mock import AsyncMock, Mock

import pytest

import app.telegram.bot as telegram_bot_module
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


def build_bot(
    monkeypatch: pytest.MonkeyPatch, *, environment: str = "test"
) -> tuple[TelegramBot, DummyApplication]:
    dummy_app = DummyApplication()

    class DummyBuilder:
        def token(self, token: str) -> "DummyBuilder":
            self.token_value = token
            return self

        def build(self) -> DummyApplication:
            return dummy_app

    monkeypatch.setattr(telegram_bot_module, "ApplicationBuilder", lambda: DummyBuilder())
    bot = TelegramBot(token="dummy-token", environment=environment)  # noqa: S106
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

        async def reply_text(self, text: str) -> None:
            self.text = text

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

    assert dummy_message.text.startswith("Привет, Антон")
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
