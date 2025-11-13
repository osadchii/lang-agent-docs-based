from __future__ import annotations

from types import SimpleNamespace
from unittest.mock import Mock

import pytest

import app.telegram.polling as polling


def test_polling_run_invokes_application_run(monkeypatch: pytest.MonkeyPatch) -> None:
    runner = Mock()
    stub_bot = SimpleNamespace(
        application=SimpleNamespace(run_polling=runner),
        allowed_updates=("message", "callback_query"),
    )
    monkeypatch.setattr(polling, "configure_logging", Mock())
    monkeypatch.setattr(polling, "telegram_bot", stub_bot)

    polling.run()

    runner.assert_called_once_with(
        allowed_updates=list(stub_bot.allowed_updates),
        drop_pending_updates=True,
    )
