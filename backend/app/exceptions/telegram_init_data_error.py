"""Exceptions related to Telegram WebApp initData validation."""


class TelegramInitDataError(Exception):
    """Raised when Telegram initData fails validation."""

    def __init__(self, message: str, *, status_code: int, error_code: str) -> None:
        super().__init__(message)
        self.status_code = status_code
        self.error_code = error_code
