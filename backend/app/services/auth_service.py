"""Authentication service coordinating initData validation and JWT issuance."""

from datetime import datetime
from typing import Tuple
from uuid import UUID

from jose import JWTError

from app.core.config import settings
from app.core.security import create_access_token, decode_access_token
from app.core.telegram import validate_web_app_init_data
from app.exceptions.telegram_init_data_error import TelegramInitDataError
from app.models.user import User
from app.repositories.user_repository import UserRepository, user_repository


class AuthService:
    """Business logic around user authentication."""

    def __init__(
        self,
        *,
        user_repository: UserRepository,
        telegram_bot_token: str,
        init_data_ttl_seconds: int,
    ) -> None:
        self._user_repository = user_repository
        self._telegram_bot_token = telegram_bot_token
        self._init_data_ttl_seconds = init_data_ttl_seconds

    def validate_init_data_and_issue_token(self, init_data: str) -> Tuple[User, str, datetime]:
        """Validate Telegram initData and issue a JWT token."""

        telegram_user = validate_web_app_init_data(
            init_data,
            self._telegram_bot_token,
            self._init_data_ttl_seconds,
        )
        user = self._user_repository.upsert_from_telegram_user(telegram_user)
        token, expires_at = create_access_token(user)
        return user, token, expires_at

    def get_user_from_token(self, token: str) -> User:
        """Decode JWT token and return the corresponding user."""

        try:
            payload = decode_access_token(token)
        except JWTError as exc:  # pragma: no cover - handled by caller
            raise ValueError("Invalid token") from exc

        user_id_value = payload.get("user_id")
        if not user_id_value:
            raise ValueError("Token missing user identifier")

        try:
            user_id = UUID(user_id_value)
        except ValueError as exc:  # pragma: no cover - invalid UUID
            raise ValueError("Token contains malformed user identifier") from exc

        user = self._user_repository.get_by_id(user_id)
        if not user:
            raise ValueError("User not found")

        return user


def get_auth_service() -> AuthService:
    """Factory returning an AuthService instance with current settings."""

    return AuthService(
        user_repository=user_repository,
        telegram_bot_token=settings.TELEGRAM_BOT_TOKEN,
        init_data_ttl_seconds=settings.TELEGRAM_INIT_DATA_TTL_SECONDS,
    )
