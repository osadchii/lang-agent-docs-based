from __future__ import annotations

import importlib
from types import ModuleType

import pytest

from app.core import version as version_module


@pytest.fixture()
def fresh_version_module() -> ModuleType:
    return importlib.reload(version_module)


def test_read_pyproject_version_returns_project_version(fresh_version_module: ModuleType) -> None:
    assert fresh_version_module._read_pyproject_version() == "0.1.0"


def test_resolve_version_uses_pyproject_fallback(monkeypatch: pytest.MonkeyPatch) -> None:
    module = importlib.reload(version_module)

    def _raise(_: str) -> str:
        raise module.PackageNotFoundError

    monkeypatch.setattr(module, "version", _raise)
    monkeypatch.setattr(module, "_read_pyproject_version", lambda: "9.9.9")

    assert module._resolve_version() == "9.9.9"


def test_resolve_version_defaults_when_no_metadata(monkeypatch: pytest.MonkeyPatch) -> None:
    module = importlib.reload(version_module)

    def _raise(_: str) -> str:
        raise module.PackageNotFoundError

    monkeypatch.setattr(module, "version", _raise)
    monkeypatch.setattr(module, "_read_pyproject_version", lambda: None)

    assert module._resolve_version() == "0.0.0"
