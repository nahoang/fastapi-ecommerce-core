"""Base schemas and response envelopes for the API layer.

This module defines standardized Pydantic v2 models for API requests,
responses, generic envelopes, pagination, and error representations.
These schemas act as Data Transfer Objects (DTOs) between the HTTP API
and the internal application/domain layers.
"""

from datetime import datetime
from typing import Generic, TypeVar
from pydantic import BaseModel, ConfigDict

# TypeVar 'T' represents any data type wrapped inside ApiResponse or PaginatedResponse
# (Generic Type: like a multipurpose container that can hold any payload)
T = TypeVar("T")


class BaseSchema(BaseModel):
    """Base Schema class for all API layer DTOs.

    from_attributes=True (replaces Pydantic v1's orm_mode=True) allows Pydantic
    to read data directly from object attributes (object.attribute) instead of
    requiring dictionary keys (dict['key']), enabling smooth serialization from
    SQLAlchemy ORM models or Domain Entities.
    """

    model_config = ConfigDict(from_attributes=True)


class BaseResponseSchema(BaseSchema):
    """Base response schema containing entity identification and audit timestamps.

    Attributes:
        id: Primary key string (typically 32-character hex UUID).
        created_at: Creation timestamp in UTC.
        updated_at: Latest update timestamp in UTC.
    """

    id: str
    created_at: datetime
    updated_at: datetime


class ApiResponse(BaseModel, Generic[T]):
    """Standardized API response envelope for single responses or custom payloads.

    Envelope standardization guarantees that client applications (web/mobile)
    always receive a consistent response structure: { "data": ..., "message": "success" }.

    Attributes:
        data: Primary payload of generic type T.
        message: Response message (defaults to 'success').
    """

    model_config = ConfigDict(from_attributes=True)

    data: T
    message: str = "success"


class PaginatedResponse(BaseModel, Generic[T]):
    """Standardized paginated API response envelope for lists of records.

    Attributes:
        data: List of items of generic type T on current page.
        total: Total number of records matching the query.
        page: Current page number (1-indexed).
        page_size: Maximum number of records per page.
        has_next: Boolean flag indicating if subsequent pages exist.
    """

    model_config = ConfigDict(from_attributes=True)

    data: list[T]
    total: int
    page: int
    page_size: int
    has_next: bool

    @classmethod
    def create(
        cls,
        data: list[T],
        total: int,
        page: int,
        page_size: int,
    ) -> "PaginatedResponse[T]":
        """Factory method that automatically computes has_next based on page and page_size.

        Args:
            data: Items for the current page.
            total: Total record count in database.
            page: Current page (1-indexed).
            page_size: Number of items per page.

        Returns:
            PaginatedResponse instance with computed has_next flag.
        """
        has_next = (page * page_size) < total
        return cls(
            data=data,
            total=total,
            page=page,
            page_size=page_size,
            has_next=has_next,
        )


class ErrorResponse(BaseModel):
    """Standardized error response payload for the entire API.

    Attributes:
        detail: Human-readable error description returned to client.
        error_code: Machine-readable uppercase identifier (e.g. 'NOT_FOUND', 'VALIDATION_ERROR').
    """

    model_config = ConfigDict(from_attributes=True)

    detail: str
    error_code: str | None = None

