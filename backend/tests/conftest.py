"""Shared pytest fixtures."""

import pytest

from app.core.config import settings
from app.repositories.profile_repository import profile_repository
from app.repositories.user_repository import user_repository
from tests.helpers import TEST_BOT_TOKEN, TEST_SECRET_KEY


@pytest.fixture(autouse=True)
def configure_environment():
    """Ensure deterministic settings for tests and reset repositories."""

    original_bot_token = settings.TELEGRAM_BOT_TOKEN
    original_secret_key = settings.SECRET_KEY
    original_security_headers = settings.SECURITY_HEADERS_ENABLED

    settings.TELEGRAM_BOT_TOKEN = TEST_BOT_TOKEN
    settings.SECRET_KEY = TEST_SECRET_KEY
    settings.SECURITY_HEADERS_ENABLED = True
    user_repository.reset()
    profile_repository.reset()

    yield

    settings.TELEGRAM_BOT_TOKEN = original_bot_token
    settings.SECRET_KEY = original_secret_key
    settings.SECURITY_HEADERS_ENABLED = original_security_headers
    user_repository.reset()
    profile_repository.reset()
