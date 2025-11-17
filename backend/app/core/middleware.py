"""Custom FastAPI middlewares for request context and access logging."""

from __future__ import annotations

import logging
import time
from uuid import uuid4

from fastapi import Request, Response, status
from starlette.middleware.base import BaseHTTPMiddleware, RequestResponseEndpoint
from starlette.types import ASGIApp

from app.core.auth import decode_access_token
from app.core.errors import ErrorCode, error_response
from app.core.logging import bind_request_id, reset_request_id
from app.services.rate_limit import RateLimitResult, RateLimitService


class RequestIDMiddleware(BaseHTTPMiddleware):
    """Attach a stable request_id to each request for correlation."""

    header_name = "X-Request-ID"

    def __init__(self, app: ASGIApp) -> None:
        super().__init__(app)

    async def dispatch(self, request: Request, call_next: RequestResponseEndpoint) -> Response:
        incoming_request_id = request.headers.get(self.header_name)
        request_id = incoming_request_id or uuid4().hex

        request.state.request_id = request_id
        token = bind_request_id(request_id)

        try:
            response = await call_next(request)
        finally:
            reset_request_id(token)

        response.headers[self.header_name] = request_id
        return response


class AccessLogMiddleware(BaseHTTPMiddleware):
    """Emit structured access logs enriched with request metadata."""

    def __init__(self, app: ASGIApp, logger_name: str = "app.access") -> None:
        super().__init__(app)
        self.logger = logging.getLogger(logger_name)

    async def dispatch(self, request: Request, call_next: RequestResponseEndpoint) -> Response:
        start = time.perf_counter()

        try:
            response = await call_next(request)
            status_code = response.status_code
        except Exception:
            status_code = 500
            duration_ms = (time.perf_counter() - start) * 1000
            self._log(request, status_code, duration_ms)
            raise

        duration_ms = (time.perf_counter() - start) * 1000
        self._log(request, status_code, duration_ms)
        return response

    def _log(self, request: Request, status_code: int, duration_ms: float) -> None:
        client_host = request.client.host if request.client else None

        self.logger.info(
            "access",
            extra={
                "event": "access",
                "http_method": request.method,
                "http_path": request.url.path,
                "status_code": status_code,
                "duration_ms": round(duration_ms, 2),
                "client_ip": client_host,
                "user_agent": request.headers.get("user-agent"),
            },
        )


class SecurityHeadersMiddleware(BaseHTTPMiddleware):
    """
    Attach a minimal set of security headers (HSTS, X-Frame-Options, etc.).

    HSTS is only enabled when explicitly requested to avoid forcing HTTPS on
    local development hosts.
    """

    def __init__(self, app: ASGIApp, enable_hsts: bool = False) -> None:
        super().__init__(app)
        self.enable_hsts = enable_hsts

    async def dispatch(self, request: Request, call_next: RequestResponseEndpoint) -> Response:
        response = await call_next(request)

        response.headers.setdefault("X-Content-Type-Options", "nosniff")
        response.headers.setdefault("X-Frame-Options", "DENY")
        response.headers.setdefault("Referrer-Policy", "same-origin")
        response.headers.setdefault("Permissions-Policy", "camera=(), microphone=()")

        if self.enable_hsts:
            response.headers.setdefault(
                "Strict-Transport-Security",
                "max-age=31536000; includeSubDomains",
            )

        return response


class RequestSizeLimitMiddleware(BaseHTTPMiddleware):
    """Reject requests whose body exceeds the configured upper bound."""

    def __init__(self, app: ASGIApp, max_request_bytes: int) -> None:
        if max_request_bytes <= 0:
            raise ValueError("max_request_bytes must be greater than zero.")
        super().__init__(app)
        self.max_request_bytes = max_request_bytes

    async def dispatch(self, request: Request, call_next: RequestResponseEndpoint) -> Response:
        if request.scope["type"] != "http":
            return await call_next(request)

        content_length = request.headers.get("content-length")
        if content_length:
            try:
                declared = int(content_length)
                if declared > self.max_request_bytes:
                    return self._payload_too_large_response()
            except ValueError:
                # Fall back to streaming check for malformed header.
                pass

        body = await request.body()
        if len(body) > self.max_request_bytes:
            return self._payload_too_large_response()

        return await call_next(request)

    @staticmethod
    def _payload_too_large_response() -> Response:
        return error_response(
            status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
            code=ErrorCode.PAYLOAD_TOO_LARGE,
            message="Request body exceeds MAX_REQUEST_BYTES limit.",
        )


class RateLimitMiddleware(BaseHTTPMiddleware):
    """Apply per-IP and per-user rate limits before hitting the routers."""

    def __init__(self, app: ASGIApp, service: RateLimitService) -> None:
        super().__init__(app)
        self.service = service
        self.enabled = service.enabled

    async def dispatch(self, request: Request, call_next: RequestResponseEndpoint) -> Response:
        if request.scope["type"] != "http":
            return await call_next(request)
        if not self.enabled:
            return await call_next(request)

        ip_address = request.client.host if request.client else "unknown"
        ip_result = await self.service.check_ip_limit(ip_address)
        if not ip_result.allowed:
            return self._rate_limited_response(
                ip_result,
                "Too many requests from this IP address. Please try again later.",
            )

        user_result = None
        user_id = self._extract_user_id(request)
        if user_id:
            user_result = await self.service.check_user_limit(user_id)
            if not user_result.allowed:
                return self._rate_limited_response(
                    user_result,
                    "Hourly request limit reached. Slow down and try again later.",
                )

        response = await call_next(request)
        active_result = user_result or ip_result
        active_result.apply(response)
        return response

    @staticmethod
    def _extract_user_id(request: Request) -> str | None:
        auth_header = request.headers.get("Authorization")
        if not auth_header or not auth_header.startswith("Bearer "):
            return None
        token = auth_header.split(" ", 1)[1].strip()
        if not token:
            return None
        try:
            payload = decode_access_token(token)
        except Exception:  # noqa: BLE001
            return None
        user_id = payload.get("user_id")
        return str(user_id) if user_id else None

    @staticmethod
    def _rate_limited_response(result: RateLimitResult, message: str) -> Response:
        response = error_response(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            code=ErrorCode.RATE_LIMIT_EXCEEDED,
            message=message,
            retry_after=result.retry_after,
        )
        for header, value in result.headers().items():
            response.headers[header] = value
        if result.retry_after:
            response.headers["Retry-After"] = str(result.retry_after)
        return response


__all__ = [
    "AccessLogMiddleware",
    "RequestIDMiddleware",
    "RequestSizeLimitMiddleware",
    "SecurityHeadersMiddleware",
    "RateLimitMiddleware",
]
