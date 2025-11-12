"""Shared error primitives and FastAPI exception handlers."""

from __future__ import annotations

import logging
from enum import StrEnum
from http import HTTPStatus
from typing import Awaitable, Callable, Mapping, MutableMapping, Sequence, cast

from fastapi import FastAPI, Request, Response, status
from fastapi.encoders import jsonable_encoder
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from starlette.exceptions import HTTPException as StarletteHTTPException

ExceptionHandlerCallable = Callable[[Request, Exception], Awaitable[Response]]

logger = logging.getLogger("app.errors")


class ErrorCode(StrEnum):
    """Canonical error codes aligned with docs/backend-api.md."""

    # Authentication & authorization
    INVALID_INIT_DATA = "INVALID_INIT_DATA"
    AUTH_FAILED = "AUTH_FAILED"
    TOKEN_EXPIRED = "TOKEN_EXPIRED"  # noqa: S105
    FORBIDDEN = "FORBIDDEN"
    RATE_LIMIT_EXCEEDED = "RATE_LIMIT_EXCEEDED"

    # Validation
    VALIDATION_ERROR = "VALIDATION_ERROR"
    INVALID_LEVEL = "INVALID_LEVEL"
    TARGET_BELOW_CURRENT = "TARGET_BELOW_CURRENT"
    INVALID_FIELD_VALUE = "INVALID_FIELD_VALUE"

    # Resources
    USER_NOT_FOUND = "USER_NOT_FOUND"
    PROFILE_NOT_FOUND = "PROFILE_NOT_FOUND"
    DECK_NOT_FOUND = "DECK_NOT_FOUND"
    CARD_NOT_FOUND = "CARD_NOT_FOUND"
    TOPIC_NOT_FOUND = "TOPIC_NOT_FOUND"
    GROUP_NOT_FOUND = "GROUP_NOT_FOUND"
    INVITE_NOT_FOUND = "INVITE_NOT_FOUND"
    DUPLICATE_LEMMA = "DUPLICATE_LEMMA"
    DUPLICATE_LANGUAGE = "DUPLICATE_LANGUAGE"
    ALREADY_MEMBER = "ALREADY_MEMBER"
    NOT_FOUND = "NOT_FOUND"

    # Business logic
    LIMIT_REACHED = "LIMIT_REACHED"
    LAST_PROFILE = "LAST_PROFILE"
    LAST_DECK = "LAST_DECK"
    CANNOT_REMOVE_OWNER = "CANNOT_REMOVE_OWNER"
    OWNER_CANNOT_LEAVE = "OWNER_CANNOT_LEAVE"
    INVITE_EXPIRED = "INVITE_EXPIRED"
    TOO_MANY_WORDS = "TOO_MANY_WORDS"

    # Payments
    PAYMENT_REQUIRED = "PAYMENT_REQUIRED"
    SUBSCRIPTION_REQUIRED = "SUBSCRIPTION_REQUIRED"

    # External services
    LLM_SERVICE_ERROR = "LLM_SERVICE_ERROR"
    STRIPE_ERROR = "STRIPE_ERROR"
    SERVICE_UNAVAILABLE = "SERVICE_UNAVAILABLE"

    # Internal
    INTERNAL_ERROR = "INTERNAL_ERROR"
    DATABASE_ERROR = "DATABASE_ERROR"

    # Transport/common
    METHOD_NOT_ALLOWED = "METHOD_NOT_ALLOWED"
    PAYLOAD_TOO_LARGE = "PAYLOAD_TOO_LARGE"
    CONFLICT = "CONFLICT"


class ApplicationError(Exception):
    """Domain/business error that should be rendered in the public API."""

    def __init__(
        self,
        code: ErrorCode | str,
        message: str,
        *,
        status_code: int = status.HTTP_400_BAD_REQUEST,
        details: object | None = None,
        retry_after: int | None = None,
    ) -> None:
        super().__init__(message)
        self.code = str(code)
        self.message = message
        self.status_code = status_code
        self.details = details
        self.retry_after = retry_after


class NotFoundError(ApplicationError):
    """404 error with a domain specific code."""

    def __init__(
        self,
        code: ErrorCode | str,
        message: str,
        *,
        details: object | None = None,
    ) -> None:
        super().__init__(
            code=code,
            message=message,
            status_code=status.HTTP_404_NOT_FOUND,
            details=details,
        )


class ConflictError(ApplicationError):
    """409 error for duplicate/conflict scenarios."""

    def __init__(
        self,
        code: ErrorCode | str,
        message: str,
        *,
        details: object | None = None,
    ) -> None:
        super().__init__(
            code=code,
            message=message,
            status_code=status.HTTP_409_CONFLICT,
            details=details,
        )


class ExternalServiceError(ApplicationError):
    """502/503 error when dependencies fail."""

    def __init__(
        self,
        code: ErrorCode | str,
        message: str,
        *,
        status_code: int = status.HTTP_502_BAD_GATEWAY,
        details: object | None = None,
    ) -> None:
        if status_code not in (status.HTTP_502_BAD_GATEWAY, status.HTTP_503_SERVICE_UNAVAILABLE):
            raise ValueError("External service errors must map to 502 or 503.")
        super().__init__(
            code=code,
            message=message,
            status_code=status_code,
            details=details,
        )


def register_exception_handlers(app: FastAPI) -> None:
    """Attach global exception handlers to the FastAPI app."""

    app.add_exception_handler(
        ApplicationError,
        cast(ExceptionHandlerCallable, application_error_handler),
    )
    app.add_exception_handler(
        RequestValidationError,
        cast(ExceptionHandlerCallable, request_validation_exception_handler),
    )
    app.add_exception_handler(
        StarletteHTTPException,
        cast(ExceptionHandlerCallable, http_exception_handler),
    )
    app.add_exception_handler(
        Exception,
        cast(ExceptionHandlerCallable, unexpected_exception_handler),
    )


async def application_error_handler(request: Request, exc: ApplicationError) -> JSONResponse:
    return error_response(
        status_code=exc.status_code,
        code=exc.code,
        message=exc.message,
        details=exc.details,
        retry_after=exc.retry_after,
    )


async def request_validation_exception_handler(
    request: Request,
    exc: RequestValidationError,
) -> JSONResponse:
    details = _format_validation_errors(exc)
    return error_response(
        status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
        code=ErrorCode.VALIDATION_ERROR,
        message="Ошибка валидации",
        details=details or None,
    )


async def http_exception_handler(
    request: Request,
    exc: StarletteHTTPException,
) -> JSONResponse:
    detail = exc.detail
    headers = exc.headers or {}
    retry_after = _extract_retry_after(headers)

    if isinstance(detail, Mapping):
        code = _coerce_code(detail.get("code"))
        message = str(detail.get("message") or HTTPStatus(exc.status_code).phrase)
        details = detail.get("details")
    else:
        code = _default_code_for_status(exc.status_code)
        message = str(detail or HTTPStatus(exc.status_code).phrase)
        details = None

    return error_response(
        status_code=exc.status_code,
        code=code,
        message=message,
        details=details,
        retry_after=retry_after,
    )


async def unexpected_exception_handler(request: Request, exc: Exception) -> JSONResponse:
    logger.exception(
        "Unhandled exception during request",
        exc_info=(exc.__class__, exc, exc.__traceback__),
    )
    return error_response(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        code=ErrorCode.INTERNAL_ERROR,
        message="Внутренняя ошибка сервера. Попробуйте позже.",
    )


def error_response(
    *,
    status_code: int,
    code: ErrorCode | str,
    message: str,
    details: object | None = None,
    retry_after: int | None = None,
) -> JSONResponse:
    """Return JSONResponse adhering to the public error contract."""
    body = build_error_payload(code=code, message=message, details=details, retry_after=retry_after)
    return JSONResponse(content=jsonable_encoder(body), status_code=status_code)


def build_error_payload(
    *,
    code: ErrorCode | str,
    message: str,
    details: object | None = None,
    retry_after: int | None = None,
) -> dict[str, dict[str, object]]:
    error_section: dict[str, object] = {
        "code": _coerce_code(code),
        "message": message,
    }
    payload: dict[str, dict[str, object]] = {"error": error_section}

    if details is not None:
        error_section["details"] = details
    if retry_after is not None:
        error_section["retry_after"] = retry_after

    return payload


def _format_validation_errors(exc: RequestValidationError) -> dict[str, str]:
    formatted: dict[str, str] = {}
    for error in exc.errors():
        loc = error.get("loc") or ()
        field = _format_error_location(loc)
        message = error.get("msg", "Invalid value")
        if field in formatted:
            formatted[field] = f"{formatted[field]}; {message}"
        else:
            formatted[field] = message
    return formatted


def _format_error_location(location: Sequence[object]) -> str:
    filtered = [
        str(part)
        for part in location
        if part not in {"body", "query", "path"}  # hide transport-specific prefixes
    ]
    if not filtered:
        filtered = [str(part) for part in location]
    return ".".join(filtered) if filtered else "_schema"


def _default_code_for_status(status_code: int) -> str:
    mapping: dict[int, ErrorCode] = {
        status.HTTP_400_BAD_REQUEST: ErrorCode.VALIDATION_ERROR,
        status.HTTP_401_UNAUTHORIZED: ErrorCode.AUTH_FAILED,
        status.HTTP_403_FORBIDDEN: ErrorCode.FORBIDDEN,
        status.HTTP_404_NOT_FOUND: ErrorCode.NOT_FOUND,
        status.HTTP_405_METHOD_NOT_ALLOWED: ErrorCode.METHOD_NOT_ALLOWED,
        status.HTTP_409_CONFLICT: ErrorCode.CONFLICT,
        status.HTTP_413_REQUEST_ENTITY_TOO_LARGE: ErrorCode.PAYLOAD_TOO_LARGE,
        status.HTTP_429_TOO_MANY_REQUESTS: ErrorCode.RATE_LIMIT_EXCEEDED,
        status.HTTP_500_INTERNAL_SERVER_ERROR: ErrorCode.INTERNAL_ERROR,
        status.HTTP_502_BAD_GATEWAY: ErrorCode.SERVICE_UNAVAILABLE,
        status.HTTP_503_SERVICE_UNAVAILABLE: ErrorCode.SERVICE_UNAVAILABLE,
    }
    return mapping.get(status_code, ErrorCode.INTERNAL_ERROR)


def _coerce_code(code: ErrorCode | str | None) -> str:
    if code is None:
        return ErrorCode.INTERNAL_ERROR
    return str(code)


def _extract_retry_after(headers: Mapping[str, str] | list[tuple[str, str]]) -> int | None:
    retry_after_value = None
    # Starlette stores headers as either dict or list of tuples depending on FastAPI version.
    if isinstance(headers, MutableMapping):
        retry_after_value = headers.get("Retry-After") or headers.get("retry-after")
    elif isinstance(headers, list):
        for key, value in headers:
            if key.lower() == "retry-after":
                retry_after_value = value
                break
    else:
        return None

    if retry_after_value is None:
        return None

    try:
        return int(retry_after_value)
    except (TypeError, ValueError):
        return None


__all__ = [
    "ApplicationError",
    "ConflictError",
    "ErrorCode",
    "ExternalServiceError",
    "NotFoundError",
    "application_error_handler",
    "build_error_payload",
    "error_response",
    "http_exception_handler",
    "register_exception_handlers",
    "request_validation_exception_handler",
    "unexpected_exception_handler",
]
