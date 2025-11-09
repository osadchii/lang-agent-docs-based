"""In-memory repository for users (placeholder until PostgreSQL integration)."""

from datetime import datetime, timezone
from threading import Lock
from typing import Dict, Optional
from uuid import UUID, uuid4

from app.models.telegram_user import TelegramUser
from app.models.user import User


class UserRepository:
    """Stores user objects in memory for the current process."""

    def __init__(self) -> None:
        self._users: Dict[UUID, User] = {}
        self._index_by_telegram: Dict[int, UUID] = {}
        self._lock = Lock()

    def upsert_from_telegram_user(self, telegram_user: TelegramUser) -> User:
        """Create or update a user from Telegram payload."""

        with self._lock:
            existing_id = self._index_by_telegram.get(telegram_user.telegram_id)
            now = datetime.now(timezone.utc)

            if existing_id:
                existing_user = self._users[existing_id]
                updated_user = existing_user.model_copy(
                    update={
                        "first_name": telegram_user.first_name,
                        "last_name": telegram_user.last_name,
                        "username": telegram_user.username,
                        "updated_at": now,
                    }
                )
                self._users[existing_id] = updated_user
                return updated_user

            user = User(
                id=uuid4(),
                telegram_id=telegram_user.telegram_id,
                first_name=telegram_user.first_name,
                last_name=telegram_user.last_name,
                username=telegram_user.username,
                updated_at=now,
                created_at=now,
            )
            self._users[user.id] = user
            self._index_by_telegram[user.telegram_id] = user.id
            return user

    def get_by_id(self, user_id: UUID) -> Optional[User]:
        """Return user by identifier if present."""

        return self._users.get(user_id)

    def update_user(
        self,
        user_id: UUID,
        *,
        first_name: Optional[str] = None,
        last_name: Optional[str] = None,
    ) -> Optional[User]:
        """Update mutable user fields and return the updated entity."""

        with self._lock:
            user = self._users.get(user_id)
            if not user:
                return None

            updates = {}
            if first_name is not None:
                updates["first_name"] = first_name
            if last_name is not None:
                updates["last_name"] = last_name

            if not updates:
                return user

            updates["updated_at"] = datetime.now(timezone.utc)
            updated_user = user.model_copy(update=updates)
            self._users[user_id] = updated_user
            return updated_user

    def set_premium_status(
        self,
        user_id: UUID,
        *,
        is_premium: bool,
        trial_ends_at: Optional[datetime] = None,
        premium_expires_at: Optional[datetime] = None,
    ) -> Optional[User]:
        """Update premium flags for a user (primarily for tests/admin flows)."""

        with self._lock:
            user = self._users.get(user_id)
            if not user:
                return None

            updates = {
                "is_premium": is_premium,
                "trial_ends_at": trial_ends_at,
                "premium_expires_at": premium_expires_at,
                "updated_at": datetime.now(timezone.utc),
            }
            updated_user = user.model_copy(update=updates)
            self._users[user_id] = updated_user
            return updated_user

    def reset(self) -> None:
        """Clear stored users (used in tests)."""

        with self._lock:
            self._users.clear()
            self._index_by_telegram.clear()


user_repository = UserRepository()
