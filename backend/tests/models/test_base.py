"""Tests for base model functionality."""

from __future__ import annotations

from app.models.base import TimestampMixin


def test_timestamp_mixin_has_created_at() -> None:
    """Test that TimestampMixin provides created_at."""
    assert hasattr(TimestampMixin, "created_at")


def test_timestamp_mixin_has_updated_at() -> None:
    """Test that TimestampMixin provides updated_at."""
    assert hasattr(TimestampMixin, "updated_at")


def test_soft_delete_mixin() -> None:
    """Test SoftDeleteMixin attributes."""
    from app.models.base import SoftDeleteMixin

    assert hasattr(SoftDeleteMixin, "deleted")
    assert hasattr(SoftDeleteMixin, "deleted_at")


def test_guid_type() -> None:
    """Test GUID type exists."""
    from app.models.base import GUID

    assert GUID is not None
