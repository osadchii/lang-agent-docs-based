from __future__ import annotations

import pytest

from app.core.config import Settings


def test_settings_cors_origins_merge_all_sources() -> None:
    settings = Settings(
        BACKEND_CORS_ORIGINS="https://foo.example.com, https://bar.example.com/",
        PRODUCTION_APP_ORIGIN="https://prod.example.com/",
    )

    assert set(settings.cors_origins) == {
        "https://bar.example.com",
        "https://foo.example.com",
        "https://prod.example.com",
        "https://webapp.telegram.org",
    }


def test_settings_parse_cors_origins_rejects_invalid_type() -> None:
    with pytest.raises(ValueError):
        Settings.parse_cors_origins(42)  # type: ignore[arg-type]
