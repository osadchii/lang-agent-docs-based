"""Telegram-specific helpers (initData validation)."""

from __future__ import annotations

import hashlib
import hmac
import json
import time
from datetime import datetime, timezone
from typing import Dict
from urllib.parse import parse_qsl

from app.core.logging import get_logger
from app.exceptions.telegram_init_data_error import TelegramInitDataError
from app.models.telegram_user import TelegramUser

logger = get_logger(__name__)


def validate_web_app_init_data(
    init_data: str,
    bot_token: str,
    max_age_seconds: int,
) -> TelegramUser:
    """Validate Telegram WebApp initData per docs/backend-auth.md."""

    if not init_data:
        raise TelegramInitDataError(
            "initData payload is empty",
            status_code=400,
            error_code="INVALID_INIT_DATA",
        )

    parsed_data = _parse_init_data(init_data)

    received_hash = parsed_data.pop("hash", None)
    if not received_hash:
        raise TelegramInitDataError(
            "hash is missing in initData",
            status_code=400,
            error_code="INVALID_INIT_DATA",
        )

    auth_date = _validate_auth_date(parsed_data.get("auth_date"), max_age_seconds)

    data_check_string = "\n".join(f"{k}={v}" for k, v in sorted(parsed_data.items()))
    expected_hash = _calculate_expected_hash(data_check_string, bot_token)

    if not hmac.compare_digest(expected_hash, received_hash):
        raise TelegramInitDataError(
            "initData signature mismatch",
            status_code=401,
            error_code="AUTH_FAILED",
        )

    telegram_user = _extract_user(parsed_data, auth_date)
    logger.debug("Validated Telegram initData for user %s", telegram_user.telegram_id)
    return telegram_user


def _parse_init_data(init_data: str) -> Dict[str, str]:
    return dict(parse_qsl(init_data, keep_blank_values=True))


def _validate_auth_date(auth_date_str: str | None, max_age_seconds: int) -> datetime:
    try:
        auth_date_timestamp = int(auth_date_str or "0")
    except ValueError as exc:  # pragma: no cover - invalid data is handled by caller
        raise TelegramInitDataError(
            "auth_date must be an integer",
            status_code=400,
            error_code="INVALID_INIT_DATA",
        ) from exc

    if auth_date_timestamp <= 0:
        raise TelegramInitDataError(
            "auth_date is missing",
            status_code=400,
            error_code="INVALID_INIT_DATA",
        )

    now = int(time.time())
    if now - auth_date_timestamp > max_age_seconds:
        raise TelegramInitDataError(
            "initData expired",
            status_code=400,
            error_code="INVALID_INIT_DATA",
        )

    return datetime.fromtimestamp(auth_date_timestamp, tz=timezone.utc)


def _calculate_expected_hash(data_check_string: str, bot_token: str) -> str:
    if not bot_token:
        raise TelegramInitDataError(
            "Telegram bot token is not configured",
            status_code=500,
            error_code="SERVER_CONFIGURATION_ERROR",
        )

    secret_key = hmac.new(
        key="WebAppData".encode(),
        msg=bot_token.encode(),
        digestmod=hashlib.sha256,
    ).digest()

    expected_hash = hmac.new(
        key=secret_key,
        msg=data_check_string.encode(),
        digestmod=hashlib.sha256,
    ).hexdigest()

    return expected_hash


def _extract_user(parsed_data: Dict[str, str], auth_date: datetime) -> TelegramUser:
    user_payload = parsed_data.get("user")
    if not user_payload:
        raise TelegramInitDataError(
            "user payload is missing",
            status_code=400,
            error_code="INVALID_INIT_DATA",
        )

    try:
        user_data = json.loads(user_payload)
    except json.JSONDecodeError as exc:
        raise TelegramInitDataError(
            "user payload is not valid JSON",
            status_code=400,
            error_code="INVALID_INIT_DATA",
        ) from exc

    telegram_id = user_data.get("id")
    if telegram_id is None:
        raise TelegramInitDataError(
            "telegram user id is missing",
            status_code=400,
            error_code="INVALID_INIT_DATA",
        )

    return TelegramUser(
        telegram_id=int(telegram_id),
        first_name=user_data.get("first_name"),
        last_name=user_data.get("last_name"),
        username=user_data.get("username"),
        language_code=user_data.get("language_code"),
        auth_date=auth_date,
    )
