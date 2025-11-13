"""
Configuration module for the Lang Agent backend.

The Settings object centralizes environment-driven configuration with strict
typing and validation rules so that the rest of the codebase can rely on a
single source of truth.
"""

from __future__ import annotations

import json
from functools import lru_cache
from typing import Literal, cast

from pydantic import (
    AliasChoices,
    AnyHttpUrl,
    Field,
    SecretStr,
    ValidationInfo,
    computed_field,
    field_validator,
    model_validator,
)
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

    database_url: str = Field(alias="DATABASE_URL")
    redis_url: str = Field(alias="REDIS_URL")

    telegram_bot_token: SecretStr = Field(alias="TELEGRAM_BOT_TOKEN")
    telegram_webhook_url: AnyHttpUrl | None = Field(alias="TELEGRAM_WEBHOOK_URL", default=None)

    openai_api_key: SecretStr = Field(alias="OPENAI_API_KEY")
    anthropic_api_key: SecretStr | None = Field(default=None, alias="ANTHROPIC_API_KEY")
    llm_model: str = Field(default="gpt-4.1-mini", alias="LLM_MODEL")
    llm_temperature: float = Field(default=0.7, alias="LLM_TEMPERATURE")

    secret_key: SecretStr = Field(alias="SECRET_KEY")
    jwt_algorithm: Literal["HS256", "HS384", "HS512"] = Field(
        default="HS256",
        alias="JWT_ALGORITHM",
        validation_alias=AliasChoices("JWT_ALGORITHM", "ALGORITHM"),
    )
    access_token_expire_minutes: int = Field(default=30, alias="ACCESS_TOKEN_EXPIRE_MINUTES")

    production_app_origin: AnyHttpUrl | None = Field(
        default=None,
        alias="PRODUCTION_APP_ORIGIN",
    )
    raw_backend_cors_origins: str | None = Field(
        default=None,
        alias="BACKEND_CORS_ORIGINS",
        description="Comma-separated list or JSON array of localhost origins (http://localhost:PORT).",
    )
    max_request_bytes: int = Field(
        default=1_048_576,
        alias="MAX_REQUEST_BYTES",
        description="Upper bound for request bodies in bytes (default 1 MiB).",
    )

    stripe_secret_key: SecretStr | None = Field(default=None, alias="STRIPE_SECRET_KEY")
    stripe_webhook_secret: SecretStr | None = Field(default=None, alias="STRIPE_WEBHOOK_SECRET")
    stripe_price_id_basic: str | None = Field(default=None, alias="STRIPE_PRICE_ID_BASIC")
    stripe_price_id_premium: str | None = Field(default=None, alias="STRIPE_PRICE_ID_PREMIUM")

    @field_validator("database_url", "redis_url", "llm_model", mode="before")
    @classmethod
    def _strip_string(cls, value: str | None, info: ValidationInfo) -> str:
        if value is None:
            field = (info.field_name or "value").upper()
            raise ValueError(f"{field} must be provided.")
        trimmed = value.strip()
        if not trimmed:
            field = (info.field_name or "value").upper()
            raise ValueError(f"{field} must not be empty.")
        return trimmed

    @field_validator("llm_temperature")
    @classmethod
    def _validate_temperature(cls, value: float) -> float:
        if not 0 <= value <= 1:
            raise ValueError("LLM_TEMPERATURE must be within [0, 1].")
        return value

    @field_validator("access_token_expire_minutes")
    @classmethod
    def _validate_token_ttl(cls, value: int) -> int:
        if value <= 0:
            raise ValueError("ACCESS_TOKEN_EXPIRE_MINUTES must be a positive integer.")
        return value

    @field_validator("max_request_bytes")
    @classmethod
    def _validate_request_size(cls, value: int) -> int:
        if value <= 0:
            raise ValueError("MAX_REQUEST_BYTES must be a positive integer.")
        return value

    @field_validator("secret_key", "telegram_bot_token", "openai_api_key", mode="after")
    @classmethod
    def _validate_secret(cls, secret: SecretStr, info: ValidationInfo) -> SecretStr:
        if not secret.get_secret_value().strip():
            field = (info.field_name or "value").upper()
            raise ValueError(f"{field} must not be empty.")
        return secret

    @model_validator(mode="after")
    def _validate_required_tokens(self) -> "Settings":
        missing: list[str] = []

        if not self.database_url:
            missing.append("DATABASE_URL")
        if not self.redis_url:
            missing.append("REDIS_URL")
        if not self.secret_key.get_secret_value():
            missing.append("SECRET_KEY")
        if not self.telegram_bot_token.get_secret_value():
            missing.append("TELEGRAM_BOT_TOKEN")
        if not self.openai_api_key.get_secret_value():
            missing.append("OPENAI_API_KEY")

        if missing:
            joined = ", ".join(sorted(missing))
            raise ValueError(f"Missing required environment variables: {joined}")

        return self

    _LOCAL_CORS_ENVIRONMENTS = frozenset({"local", "test"})

    @computed_field(return_type=list[str])
    def backend_cors_origins(self) -> list[str]:
        """
        Return validated localhost origins for local/test development.

        Production/staging environments ignore BACKEND_CORS_ORIGINS entirely to
        avoid misconfiguration on deployed servers.
        """
        if self.environment not in self._LOCAL_CORS_ENVIRONMENTS:
            return []

        parsed = self.parse_cors_origins(self.raw_backend_cors_origins)
        return [self._validate_localhost_origin(origin) for origin in parsed]

    @staticmethod
    def parse_cors_origins(origins: str | list[str] | None) -> list[str]:
        """
        Normalize the BACKEND_CORS_ORIGINS value into a list of origins.

        Accepts either a comma-separated string, a JSON array string, or an
        explicit list of strings. Any other type raises ValueError to make
        misconfiguration obvious.
        """
        if origins is None:
            return []
        if isinstance(origins, list):
            cleaned: list[str] = []
            for origin in origins:
                if not isinstance(origin, str):
                    raise ValueError("CORS origin list entries must be strings.")
                stripped = origin.strip()
                if not stripped:
                    raise ValueError("CORS origin list entries must be non-empty strings.")
                cleaned.append(stripped.rstrip("/"))
            return cleaned
        if isinstance(origins, str):
            return Settings._parse_backend_cors_origins(origins)
        raise ValueError("CORS origins must be provided as a string or list of strings.")

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
                    return [
                        str(origin).strip().rstrip("/") for origin in parsed if str(origin).strip()
                    ]
            except json.JSONDecodeError:
                pass
        return [origin.strip().rstrip("/") for origin in normalized.split(",") if origin.strip()]

    @property
    def cors_origins(self) -> list[str]:
        """
        Compile the effective list of CORS origins.

        Always includes the Telegram WebApp origin and the production app origin.
        Localhost origins are opt-in via BACKEND_CORS_ORIGINS.
        """
        origins = {"https://webapp.telegram.org"}
        cors_base = cast(list[str], self.backend_cors_origins)
        origins.update({origin.rstrip("/") for origin in cors_base})

        if self.production_app_origin:
            origins.add(str(self.production_app_origin).rstrip("/"))

        return sorted(origins)

    @staticmethod
    def _validate_localhost_origin(origin: str) -> str:
        normalized = origin.strip().rstrip("/")
        if not normalized:
            raise ValueError("CORS origin entries must be non-empty strings.")
        if not normalized.startswith("http://localhost"):
            raise ValueError(
                "BACKEND_CORS_ORIGINS only accepts http://localhost:* origins and is honored "
                "only when APP_ENV is 'local' or 'test'. Configure PRODUCTION_APP_ORIGIN for "
                "deployed domains."
            )
        return normalized


@lru_cache
def get_settings() -> Settings:
    """Return a cached Settings instance so configuration is evaluated once."""
    # BaseSettings подтягивает обязательные значения из env/.env во время инстанцирования.
    return Settings()  # type: ignore[call-arg]


settings = get_settings()
