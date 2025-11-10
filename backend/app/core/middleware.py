"""Custom FastAPI middlewares for request context and access logging."""

from __future__ import annotations

import logging
import time
from uuid import uuid4

from fastapi import Request, Response
from starlette.middleware.base import BaseHTTPMiddleware, RequestResponseEndpoint
from starlette.types import ASGIApp

from app.core.logging import bind_request_id, reset_request_id


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


__all__ = ["AccessLogMiddleware", "RequestIDMiddleware"]
