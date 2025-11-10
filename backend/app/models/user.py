"""Domain model for application users.

Matches the fields defined in docs/backend-api.md.
"""

from datetime import datetime
from typing import Optional
from uuid import UUID

from pydantic import BaseModel, ConfigDict


class User(BaseModel):
    """User entity returned to API clients."""

    id: UUID
    telegram_id: int
    first_name: Optional[str] = None
    last_name: Optional[str] = None
    username: Optional[str] = None
    is_premium: bool = False
    trial_ends_at: Optional[datetime] = None
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)
