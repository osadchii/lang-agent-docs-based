"""
Authentication API endpoints.

Implements Telegram Mini App authentication via initData validation and JWT token management.
"""

from __future__ import annotations

import logging

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.auth import TelegramDataInvalid, create_access_token, validate_telegram_init_data
from app.core.db import get_session
from app.repositories.user import UserRepository
from app.schemas.auth import UserResponse, ValidateInitDataRequest, ValidateInitDataResponse
from app.services.user import UserService

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/auth", tags=["authentication"])


@router.post("/validate", response_model=ValidateInitDataResponse, status_code=status.HTTP_200_OK)
async def validate_init_data(
    request: ValidateInitDataRequest,
    session: AsyncSession = Depends(get_session),  # noqa: B008
) -> ValidateInitDataResponse:
    """
    Validate Telegram Mini App initData and issue JWT access token.

    **Flow:**
    1. Frontend получает initData от Telegram WebApp API
    2. Frontend отправляет initData на этот endpoint
    3. Backend валидирует HMAC-SHA256 подпись
    4. Backend создаёт или обновляет пользователя в БД
    5. Backend генерирует JWT token
    6. Frontend сохраняет JWT token и использует для всех последующих запросов

    **Security:**
    - initData must be < 1 hour old (проверка auth_date)
    - HMAC signature must match (защита от подделки)
    - Only valid Telegram users can authenticate

    **Errors:**
    - 400 INVALID_INIT_DATA: initData is malformed or expired
    - 401 AUTH_FAILED: HMAC verification failed
    - 500 INTERNAL_ERROR: Database or internal error

    Args:
        request: Request containing initData string
        session: Database session

    Returns:
        ValidateInitDataResponse with user info, JWT token, and expiration time
    """
    # Validate Telegram initData
    try:
        telegram_data = validate_telegram_init_data(request.init_data)
    except TelegramDataInvalid as e:
        logger.warning(f"initData validation failed: {e!s}")
        raise HTTPException(  # noqa: B904
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={
                "error": {
                    "code": "INVALID_INIT_DATA",
                    "message": "Invalid or expired initData",
                }
            },
        )

    # Get or create user
    try:
        user_repo = UserRepository(session)
        user_service = UserService(user_repo)

        user = await user_service.get_or_create_user(
            telegram_id=telegram_data["telegram_id"],
            first_name=telegram_data["first_name"],
            last_name=telegram_data.get("last_name"),
            username=telegram_data.get("username"),
            language_code=telegram_data.get("language_code"),
        )

        await session.commit()

        logger.info(
            f"User authenticated: user_id={user.id}, telegram_id={user.telegram_id}, "
            f"username={user.username}"
        )

    except Exception:
        logger.exception("Failed to get or create user during authentication")
        await session.rollback()
        raise HTTPException(  # noqa: B904
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail={
                "error": {
                    "code": "INTERNAL_ERROR",
                    "message": "Authentication failed due to internal error",
                }
            },
        )

    # Create JWT token
    try:
        token, expires_at = create_access_token(user)
    except Exception:
        logger.exception("Failed to create JWT token")
        raise HTTPException(  # noqa: B904
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail={
                "error": {
                    "code": "INTERNAL_ERROR",
                    "message": "Failed to create access token",
                }
            },
        )

    # Build response
    return ValidateInitDataResponse(
        user=UserResponse.model_validate(user),
        token=token,
        expires_at=expires_at,
    )


__all__ = ["router"]
