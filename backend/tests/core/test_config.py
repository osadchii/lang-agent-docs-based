from __future__ import annotations

import pytest
from pydantic import ValidationError
from pydantic_settings import PydanticBaseSettingsSource

from app.core.config import Settings

SettingsPayload = dict[str, object]


REQUIRED_KWARGS: SettingsPayload = {
    "DATABASE_URL": "postgresql+asyncpg://user:pass@localhost:5432/db",
    "REDIS_URL": "redis://localhost:6379/0",
    "TELEGRAM_BOT_TOKEN": "123456:ABCDEF",
    "OPENAI_API_KEY": "sk-test",
    "SECRET_KEY": "super-secret",
}


def make_settings_data(**overrides: object) -> SettingsPayload:
    payload: SettingsPayload = {**REQUIRED_KWARGS, **overrides}
    return payload


def build_settings(**overrides: object) -> Settings:
    return NoEnvSettings.model_validate(make_settings_data(**overrides))


class NoEnvSettings(Settings):
    """Helper subclass that ignores .env files during validation."""

    model_config = Settings.model_config.copy()
    model_config["env_file"] = ()

    @classmethod
    def settings_customise_sources(
        cls,
        settings_cls: type[Settings],
        init_settings: PydanticBaseSettingsSource,
        env_settings: PydanticBaseSettingsSource,
        dotenv_settings: PydanticBaseSettingsSource,
        file_secret_settings: PydanticBaseSettingsSource,
    ) -> tuple[PydanticBaseSettingsSource, ...]:
        return (init_settings,)


def test_settings_cors_origins_merge_all_sources() -> None:
    settings = build_settings(
        BACKEND_CORS_ORIGINS="http://localhost:5173, http://localhost:3000/",
        PRODUCTION_APP_ORIGIN="https://prod.example.com/",
    )

    assert set(settings.cors_origins) == {
        "http://localhost:3000",
        "http://localhost:5173",
        "https://prod.example.com",
        "https://webapp.telegram.org",
    }


def test_settings_parse_cors_origins_rejects_invalid_type() -> None:
    with pytest.raises(ValueError):
        Settings.parse_cors_origins(42)  # type: ignore[arg-type]


def test_settings_require_mandatory_variables() -> None:
    missing = make_settings_data()
    missing.pop("DATABASE_URL")

    with pytest.raises(ValidationError) as exc:
        NoEnvSettings.model_validate(missing)

    assert "DATABASE_URL" in str(exc.value)


def test_settings_reject_blank_database_url() -> None:
    with pytest.raises(ValidationError):
        NoEnvSettings.model_validate(make_settings_data(DATABASE_URL="   "))


def test_settings_reject_invalid_temperature() -> None:
    with pytest.raises(ValidationError):
        NoEnvSettings.model_validate(make_settings_data(LLM_TEMPERATURE=1.5))


def test_settings_reject_non_positive_token_ttl() -> None:
    with pytest.raises(ValidationError):
        NoEnvSettings.model_validate(make_settings_data(ACCESS_TOKEN_EXPIRE_MINUTES=0))


def test_settings_reject_empty_secret() -> None:
    with pytest.raises(ValidationError):
        NoEnvSettings.model_validate(make_settings_data(SECRET_KEY=""))


def test_settings_parse_cors_from_json_array() -> None:
    origins = Settings._parse_backend_cors_origins('["https://one.com", "https://two.com/"]')
    assert origins == ["https://one.com", "https://two.com"]


def test_settings_parse_cors_list_rejects_blank_entries() -> None:
    with pytest.raises(ValueError):
        Settings.parse_cors_origins(["https://ok.com", "   "])


def test_settings_rejects_non_localhost_cors_origin() -> None:
    settings = build_settings(BACKEND_CORS_ORIGINS="https://example.com")

    with pytest.raises(ValueError):
        _ = settings.backend_cors_origins


def test_settings_ignore_backend_cors_origins_outside_local_env() -> None:
    settings = build_settings(
        APP_ENV="production",
        BACKEND_CORS_ORIGINS="https://example.com",
    )

    assert settings.backend_cors_origins == []
    assert settings.cors_origins == ["https://webapp.telegram.org"]


def test_settings_backend_domain_cannot_contain_scheme() -> None:
    with pytest.raises(ValidationError):
        build_settings(BACKEND_DOMAIN="https://backend.example.com")


def test_settings_derive_webhook_url_from_backend_domain() -> None:
    settings = build_settings(
        BACKEND_DOMAIN="backend.example.com",
    )

    assert settings.telegram_webhook_base_url == "https://backend.example.com"


def test_settings_rejects_invalid_max_request_bytes() -> None:
    with pytest.raises(ValidationError):
        build_settings(MAX_REQUEST_BYTES=0)
