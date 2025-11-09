"""Generic domain error for service layer."""

from __future__ import annotations

from typing import Any, Dict, Optional


class DomainError(Exception):
    """Structured error with HTTP status and code."""

    def __init__(
        self,
        *,
        status_code: int,
        error_code: str,
        message: str,
        details: Optional[Dict[str, Any]] = None,
    ) -> None:
        super().__init__(message)
        self.status_code = status_code
        self.error_code = error_code
        self.details = details or {}
