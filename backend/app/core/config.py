"""
Configuration module for the Lang Agent backend.

The Settings object centralizes environment-driven configuration with strict
typing and validation rules so that the rest of the codebase can rely on a
single source of truth.
"""

from __future__ import annotations

from functools import lru_cache
import json
from typing import Literal

from pydantic import AnyHttpUrl, Field, SecretStr, computed_field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Application configuration loaded from environment variables."""

    model_config = SettingsConfigDict(
        env_file=(".env", "../.env"),
        env_file_encoding="utf-8",
        case_sensitive=True,
        extra="ignore",
    )

    project_name: str = Field(default="Lang Agent Backend", alias="PROJECT_NAME")
    environment: Literal["local", "test", "staging", "production"] = Field(
        default="local",
        alias="APP_ENV",
    )
    debug: bool = Field(default=False, alias="DEBUG")
    api_v1_prefix: str = Field(default="/api", alias="API_V1_PREFIX")
    log_level: str = Field(default="INFO", alias="LOG_LEVEL")

    database_url: str = Field(
        default="postgresql+asyncpg://postgres:postgres@localhost:5432/lang_agent",
        alias="DATABASE_URL",
    )
    redis_url: str = Field(
        default="redis://localhost:6379/0",
        alias="REDIS_URL",
    )

    telegram_bot_token: SecretStr | None = Field(default=None, alias="TELEGRAM_BOT_TOKEN")
    telegram_webhook_url: AnyHttpUrl | None = Field(
        default=None,
        alias="TELEGRAM_WEBHOOK_URL",
    )

    openai_api_key: SecretStr | None = Field(default=None, alias="OPENAI_API_KEY")
    llm_model: str = Field(default="gpt-4.1-mini", alias="LLM_MODEL")
    llm_temperature: float = Field(default=0.7, alias="LLM_TEMPERATURE")

    secret_key: SecretStr | None = Field(default=None, alias="SECRET_KEY")
    access_token_expire_minutes: int = Field(default=30, alias="ACCESS_TOKEN_EXPIRE_MINUTES")

    production_app_origin: AnyHttpUrl | None = Field(
        default=None,
        alias="PRODUCTION_APP_ORIGIN",
    )
    raw_backend_cors_origins: str | None = Field(
        default=None,
        alias="BACKEND_CORS_ORIGINS",
        description="Comma-separated list or JSON array of allowed CORS origins.",
    )

    @computed_field(return_type=list[str])
    @property
    def backend_cors_origins(self) -> list[str]:
        return self._parse_backend_cors_origins(self.raw_backend_cors_origins)

    @staticmethod
    def _parse_backend_cors_origins(value: str | None) -> list[str]:
        if value is None:
            return []
        normalized = value.strip()
        if not normalized:
            return []
        if normalized.startswith("["):
            try:
                parsed = json.loads(normalized)
                if isinstance(parsed, list):
                    return [str(origin).strip().rstrip("/") for origin in parsed if str(origin).strip()]
            except json.JSONDecodeError:
                pass
        return [origin.strip().rstrip("/") for origin in normalized.split(",") if origin.strip()]

    @property
    def cors_origins(self) -> list[str]:
        """
        Compile the effective list of CORS origins.

        Always includes the Telegram WebApp origin in addition to the allowed
        origins supplied via configuration and the production app origin.
        """
        origins = {"https://webapp.telegram.org"}
        origins.update({origin.rstrip("/") for origin in self.backend_cors_origins})

        if self.production_app_origin:
            origins.add(str(self.production_app_origin).rstrip("/"))

        return sorted(origins)


@lru_cache
def get_settings() -> Settings:
    """Return a cached Settings instance so configuration is evaluated once."""
    return Settings()


settings = get_settings()
