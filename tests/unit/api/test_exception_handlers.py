"""Unit tests for global exception handlers and domain error mapping."""

import pytest
from fastapi import FastAPI
from httpx import ASGITransport, AsyncClient

from src.api.common.exception_handlers import register_exception_handlers
from src.api.main import app as main_app
from src.domain.common.exceptions import (
    DomainException,
    DuplicateEntityException,
    EntityNotFoundException,
    InsufficientStockException,
    InvalidOperationException,
)


@pytest.fixture
def test_app() -> FastAPI:
    """Create an isolated test FastAPI application with registered exception handlers."""
    app = FastAPI()
    register_exception_handlers(app)

    @app.get("/test/not-found")
    async def trigger_not_found():
        raise EntityNotFoundException("Product", "abc123")

    @app.get("/test/duplicate")
    async def trigger_duplicate():
        raise DuplicateEntityException(
            message="Product with slug 't-shirt' already exists",
            error_code="DUPLICATE_SLUG",
        )

    @app.get("/test/insufficient-stock")
    async def trigger_insufficient_stock():
        raise InsufficientStockException(
            message="Only 2 items remaining in inventory",
            error_code="INSUFFICIENT_STOCK",
        )

    @app.get("/test/invalid-operation")
    async def trigger_invalid_operation():
        raise InvalidOperationException(
            message="Cannot cancel an order that is already completed",
            error_code="ORDER_ALREADY_COMPLETED",
        )

    @app.get("/test/domain-catchall")
    async def trigger_domain_catchall():
        raise DomainException(
            message="Custom domain business error",
            error_code="CUSTOM_BUSINESS_ERROR",
        )

    @app.get("/test/unhandled-500")
    async def trigger_unhandled_500():
        raise RuntimeError("Unexpected internal crash simulation")

    return app


@pytest.mark.asyncio
async def test_entity_not_found_returns_404(test_app: FastAPI) -> None:
    """Verify that EntityNotFoundException maps to HTTP 404 and ErrorResponse schema."""
    async with AsyncClient(
        transport=ASGITransport(app=test_app),
        base_url="http://test",
    ) as client:
        response = await client.get("/test/not-found")

        assert response.status_code == 404
        data = response.json()
        assert data["detail"] == "Product with id 'abc123' not found"
        assert data["error_code"] == "ENTITY_NOT_FOUND"


@pytest.mark.asyncio
async def test_duplicate_entity_returns_409(test_app: FastAPI) -> None:
    """Verify that DuplicateEntityException maps to HTTP 409 Conflict."""
    async with AsyncClient(
        transport=ASGITransport(app=test_app),
        base_url="http://test",
    ) as client:
        response = await client.get("/test/duplicate")

        assert response.status_code == 409
        data = response.json()
        assert data["detail"] == "Product with slug 't-shirt' already exists"
        assert data["error_code"] == "DUPLICATE_SLUG"


@pytest.mark.asyncio
async def test_insufficient_stock_returns_409(test_app: FastAPI) -> None:
    """Verify that InsufficientStockException maps to HTTP 409 Conflict."""
    async with AsyncClient(
        transport=ASGITransport(app=test_app),
        base_url="http://test",
    ) as client:
        response = await client.get("/test/insufficient-stock")

        assert response.status_code == 409
        data = response.json()
        assert data["detail"] == "Only 2 items remaining in inventory"
        assert data["error_code"] == "INSUFFICIENT_STOCK"


@pytest.mark.asyncio
async def test_invalid_operation_returns_400(test_app: FastAPI) -> None:
    """Verify that InvalidOperationException maps to HTTP 400 Bad Request."""
    async with AsyncClient(
        transport=ASGITransport(app=test_app),
        base_url="http://test",
    ) as client:
        response = await client.get("/test/invalid-operation")

        assert response.status_code == 400
        data = response.json()
        assert data["detail"] == "Cannot cancel an order that is already completed"
        assert data["error_code"] == "ORDER_ALREADY_COMPLETED"


@pytest.mark.asyncio
async def test_domain_exception_catchall_returns_400(test_app: FastAPI) -> None:
    """Verify that generic DomainException catch-all maps to HTTP 400 Bad Request."""
    async with AsyncClient(
        transport=ASGITransport(app=test_app),
        base_url="http://test",
    ) as client:
        response = await client.get("/test/domain-catchall")

        assert response.status_code == 400
        data = response.json()
        assert data["detail"] == "Custom domain business error"
        assert data["error_code"] == "CUSTOM_BUSINESS_ERROR"


@pytest.mark.asyncio
async def test_unhandled_exception_returns_500(test_app: FastAPI) -> None:
    """Verify that unhandled server exceptions map to HTTP 500 with sanitized message."""
    async with AsyncClient(
        transport=ASGITransport(app=test_app, raise_app_exceptions=False),
        base_url="http://test",
    ) as client:
        response = await client.get("/test/unhandled-500")

        assert response.status_code == 500
        data = response.json()
        assert data["detail"] == "An unexpected internal server error occurred."
        assert data["error_code"] == "INTERNAL_SERVER_ERROR"


def test_main_app_has_exception_handlers_registered() -> None:
    """Verify that main_app has registered all required domain exception handlers."""
    assert EntityNotFoundException in main_app.exception_handlers
    assert DuplicateEntityException in main_app.exception_handlers
    assert InsufficientStockException in main_app.exception_handlers
    assert InvalidOperationException in main_app.exception_handlers
    assert DomainException in main_app.exception_handlers
    assert Exception in main_app.exception_handlers

