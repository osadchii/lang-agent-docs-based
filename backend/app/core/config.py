"""
Application configuration.

Loads settings from environment variables using Pydantic.
Follows the settings specification from docs/deployment.md.
"""

from functools import lru_cache
from typing import Optional

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """
    Application settings loaded from environment variables.

    All sensitive values (API keys, secrets) must be loaded from .env file
    and never hardcoded in the application.

    See .env.example for the full list of required variables.
    """

    model_config = SettingsConfigDict(
        env_file=".env",
        case_sensitive=True,
        extra="allow"
    )

    # Application
    APP_VERSION: str = "0.1.0"
    ENVIRONMENT: str = "development"  # development | staging | production

    # Database
    DATABASE_URL: str = "postgresql+asyncpg://postgres:dev_password@localhost:5432/langagent_dev"

    # Redis
    REDIS_URL: str = "redis://localhost:6379/0"

    # Telegram
    TELEGRAM_BOT_TOKEN: str = ""
    TELEGRAM_WEBHOOK_URL: Optional[str] = None
    TELEGRAM_INIT_DATA_TTL_SECONDS: int = 3600

    # OpenAI/LLM
    OPENAI_API_KEY: str = ""
    LLM_MODEL: str = "gpt-4.1-mini"
    LLM_TEMPERATURE: float = 0.7

    # Anthropic (optional)
    ANTHROPIC_API_KEY: Optional[str] = None

    # JWT/Security
    SECRET_KEY: str = "dev-secret-key-change-in-production"
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 30
    SECURITY_HEADERS_ENABLED: bool = True

    # Stripe
    STRIPE_SECRET_KEY: Optional[str] = None
    STRIPE_WEBHOOK_SECRET: Optional[str] = None
    STRIPE_PRICE_ID_BASIC: Optional[str] = None
    STRIPE_PRICE_ID_PREMIUM: Optional[str] = None


@lru_cache
def get_settings() -> Settings:
    """Return cached application settings instance."""

    return Settings()


settings = get_settings()
