"""
Authentication module for Telegram Mini App and JWT management.

This module implements:
1. Telegram initData validation (HMAC-SHA256)
2. JWT token creation and verification
3. Current user dependency for FastAPI routes
"""

from __future__ import annotations

import hashlib
import hmac
import json
import logging
import time
from datetime import datetime, timedelta, timezone
from typing import Any
from urllib.parse import parse_qsl
from uuid import UUID

import jwt
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.core.db import get_session
from app.core.errors import ErrorCode
from app.models.user import User
from app.repositories.user import UserRepository

logger = logging.getLogger(__name__)

security = HTTPBearer()


class TelegramDataInvalid(Exception):
    """Raised when Telegram initData validation fails."""

    pass


def validate_telegram_init_data(init_data: str) -> dict[str, Any]:
    """
    Validate Telegram WebApp initData using HMAC-SHA256.

    The validation algorithm:
    1. Parse initData string into key-value pairs
    2. Extract and remove the hash parameter
    3. Check auth_date (must be < 1 hour old)
    4. Create data_check_string (sorted key=value pairs separated by \n)
    5. Compute secret_key = HMAC-SHA256("WebAppData", bot_token)
    6. Compute expected_hash = HMAC-SHA256(data_check_string, secret_key)
    7. Compare expected_hash with received hash (constant-time comparison)

    Args:
        init_data: The initData string from Telegram WebApp.initData

    Returns:
        Dictionary with validated user data:
        {
            'telegram_id': int,
            'first_name': str,
            'last_name': str | None,
            'username': str | None,
            'language_code': str | None,
        }

    Raises:
        TelegramDataInvalid: If validation fails for any reason
    """
    try:
        # 1. Parse initData
        parsed_data = dict(parse_qsl(init_data))

        # 2. Extract hash
        received_hash = parsed_data.pop("hash", None)
        if not received_hash:
            logger.warning("initData validation failed: missing hash")
            raise TelegramDataInvalid("Missing hash in initData")

        # 3. Check auth_date (not older than 1 hour)
        auth_date_str = parsed_data.get("auth_date")
        if not auth_date_str:
            logger.warning("initData validation failed: missing auth_date")
            raise TelegramDataInvalid("Missing auth_date in initData")

        auth_date = int(auth_date_str)
        current_timestamp = int(time.time())

        # Allow 1 hour window
        if current_timestamp - auth_date > 3600:
            logger.warning(
                f"initData validation failed: expired (auth_date={auth_date}, "
                f"current={current_timestamp}, diff={current_timestamp - auth_date}s)"
            )
            raise TelegramDataInvalid("initData expired (older than 1 hour)")

        # 4. Create data_check_string (sorted key=value pairs separated by \n)
        data_check_string = "\n".join(f"{k}={v}" for k, v in sorted(parsed_data.items()))

        # 5. Compute secret_key = HMAC-SHA256("WebAppData", bot_token)
        bot_token = settings.telegram_bot_token.get_secret_value()
        secret_key = hmac.new(
            key="WebAppData".encode("utf-8"),
            msg=bot_token.encode("utf-8"),
            digestmod=hashlib.sha256,
        ).digest()

        # 6. Compute expected_hash = HMAC-SHA256(data_check_string, secret_key)
        expected_hash = hmac.new(
            key=secret_key,
            msg=data_check_string.encode("utf-8"),
            digestmod=hashlib.sha256,
        ).hexdigest()

        # 7. Compare hashes (constant-time comparison)
        if not hmac.compare_digest(expected_hash, received_hash):
            logger.warning("initData validation failed: hash mismatch")
            raise TelegramDataInvalid("Hash verification failed")

        # 8. Extract user data
        user_json = parsed_data.get("user")
        if not user_json:
            logger.warning("initData validation failed: missing user data")
            raise TelegramDataInvalid("Missing user data in initData")

        user_data = json.loads(user_json)

        telegram_id = user_data.get("id")
        if not telegram_id:
            logger.warning("initData validation failed: missing user.id")
            raise TelegramDataInvalid("Missing user.id in initData")

        logger.info(f"initData validated successfully for telegram_id={telegram_id}")

        return {
            "telegram_id": telegram_id,
            "first_name": user_data.get("first_name", ""),
            "last_name": user_data.get("last_name"),
            "username": user_data.get("username"),
            "language_code": user_data.get("language_code"),
        }

    except (ValueError, KeyError, json.JSONDecodeError) as e:
        logger.exception("initData validation failed with exception")
        raise TelegramDataInvalid(f"Invalid initData format: {e}") from e


def create_access_token(user: User) -> tuple[str, datetime]:
    """
    Create a JWT access token for the user.

    Args:
        user: User model instance

    Returns:
        Tuple of (token_string, expires_at_datetime)
    """
    now = datetime.now(timezone.utc)
    expires_at = now + timedelta(minutes=settings.access_token_expire_minutes)

    # JWT payload
    payload = {
        "user_id": str(user.id) if user.id else None,
        "telegram_id": user.telegram_id,
        "is_premium": user.is_premium,
        "iat": int(now.timestamp()),  # issued at
        "exp": int(expires_at.timestamp()),  # expiration time
    }

    # Create JWT token
    token = jwt.encode(
        payload,
        settings.secret_key.get_secret_value(),
        algorithm=settings.jwt_algorithm,
    )

    logger.info(
        f"JWT token created for user_id={user.id}, telegram_id={user.telegram_id}, "
        f"expires_at={expires_at.isoformat()}"
    )

    return token, expires_at


def decode_access_token(token: str) -> dict[str, Any]:
    """
    Decode and validate a JWT access token.

    Args:
        token: JWT token string

    Returns:
        Decoded payload dictionary

    Raises:
        jwt.ExpiredSignatureError: Token has expired
        jwt.InvalidTokenError: Token is invalid
    """
    try:
        payload: dict[str, Any] = jwt.decode(
            token,
            settings.secret_key.get_secret_value(),
            algorithms=[settings.jwt_algorithm],
        )
        return payload
    except jwt.ExpiredSignatureError:
        logger.warning("JWT token expired")
        raise
    except jwt.InvalidTokenError:
        logger.warning("JWT token invalid")
        raise


async def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(security),  # noqa: B008
    session: AsyncSession = Depends(get_session),  # noqa: B008
) -> User:
    """
    FastAPI dependency to get the current authenticated user from JWT token.

    Usage in routes:
    ```python
    @app.get("/api/users/me")
    async def get_me(current_user: User = Depends(get_current_user)):
        return serialize_user(current_user)
    ```

    Args:
        credentials: HTTP Bearer token from Authorization header
        session: Database session

    Returns:
        User model instance

    Raises:
        HTTPException 401: If token is invalid, expired, or user not found
    """
    token = credentials.credentials

    try:
        # Decode JWT
        payload = decode_access_token(token)

        user_id_str = payload.get("user_id")
        if not user_id_str:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid token: missing user_id",
            )

        # Convert to UUID
        try:
            user_id = UUID(user_id_str)
        except ValueError as exc:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid token: malformed user_id",
            ) from exc

        # Get user from database
        user_repo = UserRepository(session)
        user = await user_repo.get(user_id)

        if not user:
            logger.warning(f"User not found for user_id={user_id} from valid token")
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="User not found",
            )

        return user

    except jwt.ExpiredSignatureError as exc:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token expired",
            headers={"WWW-Authenticate": "Bearer"},
        ) from exc
    except jwt.InvalidTokenError as exc:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid token",
            headers={"WWW-Authenticate": "Bearer"},
        ) from exc


async def require_admin(user: User = Depends(get_current_user)) -> User:  # noqa: B008
    """
    Ensure the authenticated user has administrator privileges.

    Raises:
        HTTPException 403: if the user is not marked as admin.
    """

    if not getattr(user, "is_admin", False):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail={"code": ErrorCode.FORBIDDEN, "message": "Admin privileges required."},
        )
    return user
