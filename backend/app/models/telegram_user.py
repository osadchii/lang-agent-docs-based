"""Telegram WebApp user payload extracted from initData."""

from datetime import datetime
from typing import Optional

from pydantic import BaseModel, ConfigDict


class TelegramUser(BaseModel):
    """Validated Telegram user payload from WebApp initData."""

    telegram_id: int
    first_name: Optional[str] = None
    last_name: Optional[str] = None
    username: Optional[str] = None
    language_code: Optional[str] = None
    auth_date: datetime

    model_config = ConfigDict(from_attributes=True)
