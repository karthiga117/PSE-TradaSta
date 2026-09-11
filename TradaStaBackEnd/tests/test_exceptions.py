"""Exception handling tests."""

import pytest
from fastapi import FastAPI
from httpx import ASGITransport, AsyncClient

from app.core.exceptions import ApplicationException, register_exception_handlers


@pytest.mark.asyncio
async def test_application_exception_returns_consistent_error() -> None:
    application = FastAPI()
    register_exception_handlers(application)

    @application.get("/failure")
    async def failure() -> None:
        raise ApplicationException("A requested operation failed.", "OPERATION_FAILED", 422)

    async with AsyncClient(
        transport=ASGITransport(app=application), base_url="http://test"
    ) as client:
        response = await client.get("/failure")

    assert response.status_code == 422
    assert response.json() == {
        "error": {"code": "OPERATION_FAILED", "message": "A requested operation failed."}
    }
