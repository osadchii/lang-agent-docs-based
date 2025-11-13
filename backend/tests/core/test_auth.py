"""Tests for authentication functions."""

from __future__ import annotations

import hashlib
import hmac
import json
import time
from unittest.mock import AsyncMock, patch

import jwt
import pytest
from fastapi import HTTPException

from app.core.auth import (
    TelegramDataInvalid,
    create_access_token,
    decode_access_token,
    get_current_user,
    validate_telegram_init_data,
)
from app.core.config import settings
from app.models.user import User


def create_valid_init_data(telegram_id: int = 123456789) -> str:
    """Helper to create valid initData for testing."""
    auth_date = int(time.time())
    user_data = {
        "id": telegram_id,
        "first_name": "John",
        "last_name": "Doe",
        "username": "johndoe",
        "language_code": "en",
    }

    # Create data_check_string
    data = {
        "auth_date": str(auth_date),
        "user": json.dumps(user_data, separators=(",", ":")),
    }
    data_check_string = "\n".join(f"{k}={v}" for k, v in sorted(data.items()))

    # Compute hash
    bot_token = settings.telegram_bot_token.get_secret_value()
    secret_key = hmac.new(
        key="WebAppData".encode("utf-8"),
        msg=bot_token.encode("utf-8"),
        digestmod=hashlib.sha256,
    ).digest()
    hash_value = hmac.new(
        key=secret_key,
        msg=data_check_string.encode("utf-8"),
        digestmod=hashlib.sha256,
    ).hexdigest()

    # Build initData string
    return f"auth_date={auth_date}&user={data['user']}&hash={hash_value}"


def test_validate_telegram_init_data_success() -> None:
    """Test successful validation of Telegram initData."""
    init_data = create_valid_init_data(telegram_id=123456789)
    result = validate_telegram_init_data(init_data)

    assert result["telegram_id"] == 123456789
    assert result["first_name"] == "John"
    assert result["last_name"] == "Doe"
    assert result["username"] == "johndoe"
    assert result["language_code"] == "en"


def test_validate_telegram_init_data_missing_hash() -> None:
    """Test validation fails when hash is missing."""
    init_data = "auth_date=1234567890&user=%7B%22id%22%3A123%7D"

    with pytest.raises(TelegramDataInvalid, match="Missing hash"):
        validate_telegram_init_data(init_data)


def test_validate_telegram_init_data_missing_auth_date() -> None:
    """Test validation fails when auth_date is missing."""
    init_data = "user=%7B%22id%22%3A123%7D&hash=abc123"

    with pytest.raises(TelegramDataInvalid, match="Missing auth_date"):
        validate_telegram_init_data(init_data)


def test_validate_telegram_init_data_expired() -> None:
    """Test validation fails when initData is older than 1 hour."""
    # Create initData with old timestamp (2 hours ago)
    old_timestamp = int(time.time()) - 7200
    user_data = {"id": 123456789, "first_name": "John"}
    data = {
        "auth_date": str(old_timestamp),
        "user": json.dumps(user_data, separators=(",", ":")),
    }
    data_check_string = "\n".join(f"{k}={v}" for k, v in sorted(data.items()))

    bot_token = settings.telegram_bot_token.get_secret_value()
    secret_key = hmac.new(
        key="WebAppData".encode("utf-8"),
        msg=bot_token.encode("utf-8"),
        digestmod=hashlib.sha256,
    ).digest()
    hash_value = hmac.new(
        key=secret_key,
        msg=data_check_string.encode("utf-8"),
        digestmod=hashlib.sha256,
    ).hexdigest()

    init_data = f"auth_date={old_timestamp}&user={data['user']}&hash={hash_value}"

    with pytest.raises(TelegramDataInvalid, match="expired"):
        validate_telegram_init_data(init_data)


def test_validate_telegram_init_data_invalid_hash() -> None:
    """Test validation fails when hash doesn't match."""
    auth_date = int(time.time())
    user_data = {"id": 123456789, "first_name": "John"}
    init_data = f"auth_date={auth_date}&user={json.dumps(user_data)}&hash=invalid_hash_123"

    with pytest.raises(TelegramDataInvalid, match="Hash verification failed"):
        validate_telegram_init_data(init_data)


def test_validate_telegram_init_data_missing_user_data() -> None:
    """Test validation fails when user data is missing."""
    auth_date = int(time.time())
    data_check_string = f"auth_date={auth_date}"

    bot_token = settings.telegram_bot_token.get_secret_value()
    secret_key = hmac.new(
        key="WebAppData".encode("utf-8"),
        msg=bot_token.encode("utf-8"),
        digestmod=hashlib.sha256,
    ).digest()
    hash_value = hmac.new(
        key=secret_key,
        msg=data_check_string.encode("utf-8"),
        digestmod=hashlib.sha256,
    ).hexdigest()

    init_data = f"auth_date={auth_date}&hash={hash_value}"

    with pytest.raises(TelegramDataInvalid, match="Missing user data"):
        validate_telegram_init_data(init_data)


def test_create_access_token() -> None:
    """Test JWT token creation."""
    user = User(
        telegram_id=123456789,
        first_name="John",
        last_name="Doe",
        username="johndoe",
        is_premium=True,
    )

    token, expires_at = create_access_token(user)

    # Verify token is a string
    assert isinstance(token, str)
    assert len(token) > 0

    # Verify expires_at is set correctly (should be ~30 minutes from now)
    assert expires_at is not None

    # Decode token to verify payload
    payload = jwt.decode(
        token,
        settings.secret_key.get_secret_value(),
        algorithms=[settings.jwt_algorithm],
    )

    assert payload["telegram_id"] == 123456789
    assert payload["is_premium"] is True
    assert "user_id" in payload
    assert "iat" in payload
    assert "exp" in payload


def test_decode_access_token_success() -> None:
    """Test successful JWT token decoding."""
    user = User(
        telegram_id=123456789,
        first_name="John",
        is_premium=False,
    )

    token, _ = create_access_token(user)
    payload = decode_access_token(token)

    assert payload["telegram_id"] == 123456789
    assert payload["is_premium"] is False
    assert "user_id" in payload


def test_decode_access_token_invalid() -> None:
    """Test decoding invalid JWT token."""
    with pytest.raises(jwt.InvalidTokenError):
        decode_access_token("invalid.token.here")


def test_decode_access_token_wrong_signature() -> None:
    """Test decoding token with wrong signature."""
    # Create token with different secret
    token = jwt.encode(
        {"user_id": "123", "telegram_id": 456},
        "wrong_secret",
        algorithm="HS256",
    )

    with pytest.raises(jwt.InvalidTokenError):
        decode_access_token(token)


@pytest.mark.asyncio
async def test_get_current_user_success() -> None:
    """Test get_current_user dependency with valid token."""
    # Create mock user
    mock_user = User(
        telegram_id=123456789,
        first_name="John",
        is_premium=False,
    )

    # Create valid token
    token, _ = create_access_token(mock_user)

    # Mock credentials
    from fastapi.security import HTTPAuthorizationCredentials

    credentials = HTTPAuthorizationCredentials(scheme="Bearer", credentials=token)

    # Mock repository
    with patch("app.core.auth.UserRepository") as mock_repo_class:
        mock_repo = mock_repo_class.return_value
        mock_repo.get = AsyncMock(return_value=mock_user)

        # Mock session
        mock_session = AsyncMock()

        # Call get_current_user
        result = await get_current_user(credentials, mock_session)

        assert result == mock_user
        mock_repo.get.assert_called_once()


@pytest.mark.asyncio
async def test_get_current_user_expired_token() -> None:
    """Test get_current_user with expired token."""
    # Create token that expired immediately
    with patch("app.core.auth.settings") as mock_settings:
        mock_settings.secret_key.get_secret_value.return_value = (
            settings.secret_key.get_secret_value()
        )
        mock_settings.jwt_algorithm = "HS256"
        mock_settings.access_token_expire_minutes = 0  # Expired immediately

        mock_user = User(telegram_id=123, first_name="Test", is_premium=False)
        token, _ = create_access_token(mock_user)

    from fastapi.security import HTTPAuthorizationCredentials

    credentials = HTTPAuthorizationCredentials(scheme="Bearer", credentials=token)
    mock_session = AsyncMock()

    # Should raise 401
    with pytest.raises(HTTPException) as exc_info:
        await get_current_user(credentials, mock_session)

    assert exc_info.value.status_code == 401
    assert "expired" in exc_info.value.detail.lower()


@pytest.mark.asyncio
async def test_get_current_user_invalid_token() -> None:
    """Test get_current_user with invalid token."""
    from fastapi.security import HTTPAuthorizationCredentials

    credentials = HTTPAuthorizationCredentials(scheme="Bearer", credentials="invalid.token.here")
    mock_session = AsyncMock()

    with pytest.raises(HTTPException) as exc_info:
        await get_current_user(credentials, mock_session)

    assert exc_info.value.status_code == 401


@pytest.mark.asyncio
async def test_get_current_user_user_not_found() -> None:
    """Test get_current_user when user doesn't exist in database."""
    mock_user = User(telegram_id=123, first_name="Test", is_premium=False)
    token, _ = create_access_token(mock_user)

    from fastapi.security import HTTPAuthorizationCredentials

    credentials = HTTPAuthorizationCredentials(scheme="Bearer", credentials=token)

    # Mock repository to return None (user not found)
    with patch("app.core.auth.UserRepository") as mock_repo_class:
        mock_repo = mock_repo_class.return_value
        mock_repo.get = AsyncMock(return_value=None)

        mock_session = AsyncMock()

        with pytest.raises(HTTPException) as exc_info:
            await get_current_user(credentials, mock_session)

        assert exc_info.value.status_code == 401
        assert "not found" in exc_info.value.detail.lower()
