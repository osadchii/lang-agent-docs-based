"""Alembic environment configuration.

This file wires Alembic to the project's settings module so that migrations
reuse the same database URL the application uses. When the application is
configured with an async driver (postgresql+asyncpg), we switch to a synchronous
driver for Alembic so migrations can run with SQLAlchemy's standard engine.
"""

from __future__ import annotations

import os
import sys
from logging.config import fileConfig
from typing import Any, Dict

from alembic import context
from sqlalchemy import engine_from_config, pool


# Ensure "backend" package is on sys.path when migrations run from CLI
BASE_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if BASE_DIR not in sys.path:
    sys.path.insert(0, BASE_DIR)

from app.core.config import settings  # noqa: E402


config = context.config

if config.config_file_name is not None:
    fileConfig(config.config_file_name)


def _get_database_url() -> str:
    """Return a sync SQLAlchemy URL derived from application settings."""

    url = settings.DATABASE_URL
    if url.startswith("postgresql+asyncpg"):
        return url.replace("+asyncpg", "+psycopg", 1)
    return url


def _get_config_section() -> Dict[str, Any]:
    section = config.get_section(config.config_ini_section) or {}
    section["sqlalchemy.url"] = _get_database_url()
    return section


# TODO: Replace with actual metadata once SQLAlchemy models are introduced
target_metadata = None


def run_migrations_offline() -> None:
    """Run migrations in 'offline' mode."""

    url = _get_database_url()
    context.configure(
        url=url,
        target_metadata=target_metadata,
        literal_binds=True,
        compare_type=True,
        compare_server_default=True,
        dialect_opts={"paramstyle": "named"},
    )

    with context.begin_transaction():
        context.run_migrations()


def run_migrations_online() -> None:
    """Run migrations in 'online' mode."""

    connectable = engine_from_config(
        _get_config_section(),
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,
    )

    with connectable.connect() as connection:
        context.configure(
            connection=connection,
            target_metadata=target_metadata,
            compare_type=True,
            compare_server_default=True,
        )

        with context.begin_transaction():
            context.run_migrations()


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
