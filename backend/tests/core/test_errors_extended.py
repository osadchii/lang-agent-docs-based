"""Extended tests for error handling."""

from __future__ import annotations

import pytest
from fastapi import status

from app.core.errors import (
    ApplicationError,
    ConflictError,
    ErrorCode,
    ExternalServiceError,
    LLMParsingError,
    NotFoundError,
)


def test_application_error_with_details() -> None:
    """Test ApplicationError with details."""
    error = ApplicationError(
        code=ErrorCode.INTERNAL_ERROR,
        message="Test error",
        status_code=500,
        details={"key": "value"},
    )
    assert error.details == {"key": "value"}


def test_not_found_error_default_status() -> None:
    """Test NotFoundError has 404 status."""
    error = NotFoundError(
        code=ErrorCode.USER_NOT_FOUND,
        message="User not found",
    )
    assert error.status_code == status.HTTP_404_NOT_FOUND


def test_conflict_error_default_status() -> None:
    """Test ConflictError has 409 status."""
    error = ConflictError(
        code=ErrorCode.DUPLICATE_LEMMA,
        message="Lemma already exists",
    )
    assert error.status_code == status.HTTP_409_CONFLICT


def test_external_service_error_502() -> None:
    """Test ExternalServiceError with 502 status."""
    error = ExternalServiceError(
        code=ErrorCode.LLM_SERVICE_ERROR,
        message="LLM service unavailable",
        status_code=status.HTTP_502_BAD_GATEWAY,
    )
    assert error.status_code == 502


def test_external_service_error_503() -> None:
    """Test ExternalServiceError with 503 status."""
    error = ExternalServiceError(
        code=ErrorCode.SERVICE_UNAVAILABLE,
        message="Service temporarily unavailable",
        status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
    )
    assert error.status_code == 503


def test_external_service_error_invalid_status() -> None:
    """Test ExternalServiceError rejects invalid status codes."""
    with pytest.raises(ValueError, match="must map to 502 or 503"):
        ExternalServiceError(
            code=ErrorCode.LLM_SERVICE_ERROR,
            message="Test",
            status_code=500,  # Invalid
        )


def test_llm_parsing_error() -> None:
    """Test LLMParsingError."""
    error = LLMParsingError("Invalid JSON")
    assert error.code == ErrorCode.LLM_SERVICE_ERROR
    assert error.status_code == status.HTTP_502_BAD_GATEWAY


def test_error_code_enum_values() -> None:
    """Test ErrorCode enum has expected values."""
    assert ErrorCode.INVALID_INIT_DATA == "INVALID_INIT_DATA"
    assert ErrorCode.USER_NOT_FOUND == "USER_NOT_FOUND"
    assert ErrorCode.LLM_SERVICE_ERROR == "LLM_SERVICE_ERROR"


def test_application_error_str() -> None:
    """Test ApplicationError string representation."""
    error = ApplicationError(
        code=ErrorCode.INTERNAL_ERROR,
        message="Test error message",
        status_code=500,
    )
    error_str = str(error)
    assert "Test error message" in error_str
