"""Global exception handlers for the FastAPI API layer.

This module maps domain-level business exceptions and unexpected server errors
to standardized HTTP status codes and ErrorResponse JSON payloads.
By centralizing error translation in this module, the domain layer remains
completely unaware of HTTP, web frameworks, and presentation concerns.
"""

import logging
from fastapi import FastAPI, Request, status
from fastapi.responses import JSONResponse

from src.api.common.schemas import ErrorResponse
from src.domain.common.exceptions import (
    DomainException,
    DuplicateEntityException,
    EntityNotFoundException,
    InsufficientStockException,
    InvalidOperationException,
)

logger = logging.getLogger(__name__)


async def entity_not_found_handler(request: Request, exc: EntityNotFoundException) -> JSONResponse:
    """Handle entity not found errors (HTTP 404 Not Found)."""
    return JSONResponse(
        status_code=status.HTTP_404_NOT_FOUND,
        content=ErrorResponse(
            detail=exc.message,
            error_code=exc.error_code or "ENTITY_NOT_FOUND",
        ).model_dump(),
    )


async def duplicate_entity_handler(request: Request, exc: DuplicateEntityException) -> JSONResponse:
    """Handle unique constraint violation errors (HTTP 409 Conflict)."""
    return JSONResponse(
        status_code=status.HTTP_409_CONFLICT,
        content=ErrorResponse(
            detail=exc.message,
            error_code=exc.error_code or "DUPLICATE_ENTITY",
        ).model_dump(),
    )


async def insufficient_stock_handler(request: Request, exc: InsufficientStockException) -> JSONResponse:
    """Handle insufficient stock / inventory exhaustion errors (HTTP 409 Conflict)."""
    return JSONResponse(
        status_code=status.HTTP_409_CONFLICT,
        content=ErrorResponse(
            detail=exc.message,
            error_code=exc.error_code or "INSUFFICIENT_STOCK",
        ).model_dump(),
    )


async def invalid_operation_handler(request: Request, exc: InvalidOperationException) -> JSONResponse:
    """Handle invalid operation for current entity state (HTTP 400 Bad Request)."""
    return JSONResponse(
        status_code=status.HTTP_400_BAD_REQUEST,
        content=ErrorResponse(
            detail=exc.message,
            error_code=exc.error_code or "INVALID_OPERATION",
        ).model_dump(),
    )


async def domain_exception_handler(request: Request, exc: DomainException) -> JSONResponse:
    """Catch-all handler for any other DomainException (HTTP 400 Bad Request)."""
    return JSONResponse(
        status_code=status.HTTP_400_BAD_REQUEST,
        content=ErrorResponse(
            detail=exc.message,
            error_code=exc.error_code or "DOMAIN_ERROR",
        ).model_dump(),
    )


async def unhandled_exception_handler(request: Request, exc: Exception) -> JSONResponse:
    """Handle unexpected server errors (HTTP 500 Internal Server Error).

    Logs full traceback for server observability while returning a safe,
    sanitized message to the client to avoid leaking sensitive internal details.
    """
    logger.exception(f"Unhandled system error occurred on path '{request.url.path}': {exc}")
    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content=ErrorResponse(
            detail="An unexpected internal server error occurred.",
            error_code="INTERNAL_SERVER_ERROR",
        ).model_dump(),
    )


def register_exception_handlers(app: FastAPI) -> None:
    """Register all domain and system exception handlers onto the FastAPI application.

    FastAPI and Starlette follow the Method Resolution Order (MRO) to match the most
    specific exception handler before falling back to generic handlers.
    """
    app.add_exception_handler(EntityNotFoundException, entity_not_found_handler)
    app.add_exception_handler(DuplicateEntityException, duplicate_entity_handler)
    app.add_exception_handler(InsufficientStockException, insufficient_stock_handler)
    app.add_exception_handler(InvalidOperationException, invalid_operation_handler)
    app.add_exception_handler(DomainException, domain_exception_handler)
    app.add_exception_handler(Exception, unhandled_exception_handler)

