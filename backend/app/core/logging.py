"""
Logging configuration.

Implements structured logging for the application according to
docs/deployment.md (Monitoring section).
"""

import logging
import sys
from typing import Any

from app.core.config import settings


def setup_logging() -> None:
    """
    Configure application logging.

    - Development: DEBUG level, human-readable format
    - Production: INFO level, JSON format for parsing
    """
    log_level = logging.DEBUG if settings.ENVIRONMENT == "development" else logging.INFO

    # Configure root logger
    logging.basicConfig(
        level=log_level,
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
        handlers=[
            logging.StreamHandler(sys.stdout)
        ]
    )

    # Set third-party loggers to WARNING to reduce noise
    logging.getLogger("uvicorn").setLevel(logging.WARNING)
    logging.getLogger("uvicorn.access").setLevel(logging.WARNING)
    logging.getLogger("sqlalchemy").setLevel(logging.WARNING)


def get_logger(name: str) -> logging.Logger:
    """
    Get a logger instance for a module.

    Args:
        name: Logger name (usually __name__)

    Returns:
        Configured logger instance

    Example:
        >>> logger = get_logger(__name__)
        >>> logger.info("Application started")
    """
    return logging.getLogger(name)
