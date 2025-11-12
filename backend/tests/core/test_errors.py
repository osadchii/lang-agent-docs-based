from __future__ import annotations

from typing import AsyncIterator, cast

import pytest
import pytest_asyncio
from fastapi import FastAPI, HTTPException
from fastapi.routing import APIRouter
from httpx import ASGITransport, AsyncClient
from pydantic import BaseModel, Field
from starlette.types import ASGIApp

from app.core.errors import ApplicationError, ErrorCode, register_exception_handlers


class EchoPayload(BaseModel):
    text: str = Field(min_length=1)


def _build_test_router() -> APIRouter:
    router = APIRouter()

    @router.get("/app-error")
    async def raise_app_error() -> None:
        raise ApplicationError(
            code=ErrorCode.LIMIT_REACHED,
            message="Достигнут лимит профилей (1 для бесплатного плана)",
            details={"limit_type": "profiles", "current": 1, "max": 1},
        )

    @router.post("/echo")
    async def echo(payload: EchoPayload) -> EchoPayload:
        return payload

    @router.get("/http-error")
    async def raise_http_exc() -> None:
        raise HTTPException(status_code=403, detail="Forbidden")

    @router.get("/http-error-with-payload")
    async def raise_http_exc_with_payload() -> None:
        raise HTTPException(
            status_code=409,
            detail={
                "code": ErrorCode.DUPLICATE_LANGUAGE,
                "message": "Профиль языка уже существует",
                "details": {"language": "en"},
            },
        )

    @router.get("/crash")
    async def raise_generic_exc() -> None:
        raise RuntimeError("boom")

    return router


@pytest.fixture(scope="module")
def error_test_app() -> FastAPI:
    app = FastAPI()
    register_exception_handlers(app)
    app.include_router(_build_test_router())
    return app


@pytest_asyncio.fixture
async def error_test_client(error_test_app: FastAPI) -> AsyncIterator[AsyncClient]:
    # FastAPI implements the ASGI callable interface but type stubs disagree.
    transport = ASGITransport(
        app=cast(ASGIApp, error_test_app),  # type: ignore[arg-type]
        raise_app_exceptions=False,
    )
    client = AsyncClient(transport=transport, base_url="http://testserver")
    try:
        yield client
    finally:
        await client.aclose()


@pytest.mark.asyncio
async def test_application_error_handler_returns_payload(error_test_client: AsyncClient) -> None:
    response = await error_test_client.get("/app-error")

    assert response.status_code == 400
    payload = response.json()["error"]
    assert payload["code"] == str(ErrorCode.LIMIT_REACHED)
    assert payload["message"].startswith("Достигнут лимит профилей")
    assert payload["details"]["limit_type"] == "profiles"


@pytest.mark.asyncio
async def test_validation_error_handler_formats_details(error_test_client: AsyncClient) -> None:
    response = await error_test_client.post("/echo", json={"text": ""})

    assert response.status_code == 422
    payload = response.json()["error"]
    assert payload["code"] == str(ErrorCode.VALIDATION_ERROR)
    assert "text" in payload["details"]


@pytest.mark.asyncio
async def test_http_exception_without_payload_uses_default_code(
    error_test_client: AsyncClient,
) -> None:
    response = await error_test_client.get("/http-error")

    assert response.status_code == 403
    payload = response.json()["error"]
    assert payload["code"] == str(ErrorCode.FORBIDDEN)
    assert payload["message"] == "Forbidden"


@pytest.mark.asyncio
async def test_http_exception_with_payload_preserves_contract(
    error_test_client: AsyncClient,
) -> None:
    response = await error_test_client.get("/http-error-with-payload")

    assert response.status_code == 409
    payload = response.json()["error"]
    assert payload["code"] == str(ErrorCode.DUPLICATE_LANGUAGE)
    assert payload["details"]["language"] == "en"


@pytest.mark.asyncio
async def test_unhandled_exception_masked_as_internal_error(
    error_test_client: AsyncClient,
) -> None:
    response = await error_test_client.get("/crash")

    assert response.status_code == 500
    payload = response.json()["error"]
    assert payload["code"] == str(ErrorCode.INTERNAL_ERROR)
    assert "Попробуйте позже" in payload["message"]
