"""Tests for main application module."""

from __future__ import annotations

from fastapi.testclient import TestClient

from app.main import app


def test_app_title() -> None:
    """Test that app has correct title."""
    assert "Lang Agent Backend" in app.title


def test_app_version() -> None:
    """Test that app has version."""
    assert hasattr(app, "version")
    assert app.version is not None


def test_app_has_exception_handlers() -> None:
    """Test that exception handlers are registered."""
    assert len(app.exception_handlers) > 0


def test_app_has_routers() -> None:
    """Test that API routers are included."""
    routes = [route.path for route in app.routes]
    assert "/health" in routes
    assert "/metrics" in routes


def test_openapi_schema() -> None:
    """Test that OpenAPI schema is generated."""
    client = TestClient(app)
    response = client.get("/openapi.json")
    assert response.status_code == 200
    schema = response.json()
    assert "openapi" in schema
    assert "paths" in schema
