"""Security utilities for JWT handling."""

from datetime import datetime, timedelta, timezone
from typing import Any, Dict, Optional, Tuple

from jose import JWTError, jwt

from app.core.config import settings
from app.core.logging import get_logger
from app.models.user import User

logger = get_logger(__name__)


def _current_time() -> datetime:
    """Return timezone-aware UTC timestamp."""

    return datetime.now(timezone.utc)


def create_access_token(
    user: User,
    expires_delta: Optional[timedelta] = None,
) -> Tuple[str, datetime]:
    """Create JWT access token according to docs/backend-auth.md."""

    issued_at = _current_time()
    expire_delta = expires_delta or timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
    expires_at = issued_at + expire_delta

    payload = {
        "user_id": str(user.id),
        "telegram_id": user.telegram_id,
        "is_premium": user.is_premium,
        "iat": int(issued_at.timestamp()),
        "exp": int(expires_at.timestamp()),
    }

    token = jwt.encode(payload, settings.SECRET_KEY, algorithm=settings.ALGORITHM)
    logger.debug("Generated JWT token for user %s", user.id)

    return token, expires_at


def decode_access_token(token: str) -> Dict[str, Any]:
    """Decode and verify JWT access token."""

    try:
        return jwt.decode(token, settings.SECRET_KEY, algorithms=[settings.ALGORITHM])
    except JWTError as exc:  # pragma: no cover - logged and re-raised
        logger.warning("Failed to decode JWT: %s", exc)
        raise
