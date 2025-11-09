"""Business logic for user endpoints."""

from __future__ import annotations

from datetime import datetime, time, timedelta, timezone
from typing import Dict

from app.exceptions.domain_error import DomainError
from app.models.user import User
from app.repositories.profile_repository import ProfileRepository, profile_repository
from app.repositories.user_repository import UserRepository, user_repository
from app.services.plan_limits import get_plan_limits


class UserService:
    """Operations that aggregate user data."""

    def __init__(
        self,
        *,
        user_repo: UserRepository,
        profile_repo: ProfileRepository,
    ) -> None:
        self._user_repo = user_repo
        self._profile_repo = profile_repo

    def get_user_overview(self, user: User) -> Dict[str, object]:
        """Return payload for GET /api/users/me."""

        limits = get_plan_limits(user)
        profiles_used = self._profile_repo.count_active(user.id)

        limits_payload: Dict[str, Dict[str, object]] = {
            "profiles": {"used": profiles_used, "max": limits.profiles},
            "messages": self._resettable_limit_payload(limits.messages),
            "exercises": self._resettable_limit_payload(limits.exercises),
            "cards": {"used": 0, "max": limits.cards},
            "groups": {"used": 0, "max": limits.groups},
        }
        limits_payload["messages"]["used"] = 0
        limits_payload["exercises"]["used"] = 0

        subscription_payload = self._subscription_payload(user)

        return {
            "id": user.id,
            "telegram_id": user.telegram_id,
            "first_name": user.first_name,
            "last_name": user.last_name,
            "username": user.username,
            "is_premium": user.is_premium,
            "trial_ends_at": user.trial_ends_at,
            "premium_expires_at": user.premium_expires_at,
            "created_at": user.created_at,
            "updated_at": user.updated_at,
            "subscription": subscription_payload,
            "limits": limits_payload,
        }

    def update_user(
        self,
        *,
        user: User,
        first_name: str | None = None,
        last_name: str | None = None,
    ) -> User:
        """Update allowed user fields."""

        if first_name is None and last_name is None:
            raise DomainError(
                status_code=400,
                error_code="INVALID_FIELD_VALUE",
                message="Не переданы поля для обновления.",
            )

        updated = self._user_repo.update_user(
            user.id,
            first_name=first_name,
            last_name=last_name,
        )
        if not updated:
            raise DomainError(
                status_code=404,
                error_code="USER_NOT_FOUND",
                message="Пользователь не найден.",
            )
        return updated

    def _resettable_limit_payload(self, limit: int | None) -> Dict[str, object]:
        reset_at = self._next_utc_midnight()
        return {
            "used": 0,
            "max": limit,
            "reset_at": reset_at if limit is not None else None,
        }

    @staticmethod
    def _next_utc_midnight() -> datetime:
        now = datetime.now(timezone.utc)
        tomorrow = now.date() + timedelta(days=1)
        return datetime.combine(tomorrow, time.min, tzinfo=timezone.utc)

    @staticmethod
    def _subscription_payload(user: User) -> Dict[str, object]:
        now = datetime.now(timezone.utc)
        if user.trial_ends_at and user.trial_ends_at > now:
            return {
                "status": "trial",
                "plan": None,
                "expires_at": user.trial_ends_at,
                "cancel_at_period_end": False,
            }
        if user.is_premium:
            return {
                "status": "active",
                "plan": "monthly",
                "expires_at": user.premium_expires_at,
                "cancel_at_period_end": False,
            }
        return {
            "status": "free",
            "plan": None,
            "expires_at": None,
            "cancel_at_period_end": False,
        }


_user_service: UserService | None = None


def get_user_service() -> UserService:
    """Return singleton user service."""

    global _user_service
    if _user_service is None:
        _user_service = UserService(
            user_repo=user_repository,
            profile_repo=profile_repository,
        )
    return _user_service
