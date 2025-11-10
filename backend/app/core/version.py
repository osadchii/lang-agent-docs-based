"""Utilities for retrieving the backend package version."""

from __future__ import annotations

from importlib.metadata import PackageNotFoundError, version
from pathlib import Path
from typing import Final

import tomllib


def _read_pyproject_version() -> str | None:
    """Extract the version from pyproject.toml when package metadata is unavailable."""
    pyproject_path = Path(__file__).resolve().parents[2] / "pyproject.toml"
    if not pyproject_path.exists():
        return None

    with pyproject_path.open("rb") as fp:
        data = tomllib.load(fp)

    project_data = data.get("project")
    if isinstance(project_data, dict):
        version_value = project_data.get("version")
        if isinstance(version_value, str):
            return version_value
    return None


def _resolve_version() -> str:
    try:
        return version("lang-agent-backend")
    except PackageNotFoundError:
        fallback_version = _read_pyproject_version()
        return fallback_version or "0.0.0"


APP_VERSION: Final[str] = _resolve_version()

__all__ = ["APP_VERSION"]
