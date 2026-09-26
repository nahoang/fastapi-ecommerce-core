"""Unit tests for Pydantic v2 base schemas and API response envelopes."""

import json
from dataclasses import dataclass
from datetime import datetime, timezone
import pytest

from src.api.common.schemas import (
    ApiResponse,
    BaseResponseSchema,
    BaseSchema,
    ErrorResponse,
    PaginatedResponse,
)


class SampleSchema(BaseResponseSchema):
    """Test schema inheriting from BaseResponseSchema."""

    name: str


@dataclass
class MockDomainEntity:
    """Mock Python object simulating a Domain Entity or ORM Model with attributes."""

    id: str
    created_at: datetime
    updated_at: datetime
    name: str


def test_base_schema_from_attributes() -> None:
    """Verify BaseSchema supports attribute reading (from_attributes=True)."""
    now = datetime.now(timezone.utc)
    mock_entity = MockDomainEntity(
        id="a1b2c3d4e5f6a1b2c3d4e5f6a1b2c3d4",
        created_at=now,
        updated_at=now,
        name="MacBook Pro M3",
    )

    # Use model_validate to convert from object to Pydantic schema
    sample = SampleSchema.model_validate(mock_entity)

    assert sample.id == "a1b2c3d4e5f6a1b2c3d4e5f6a1b2c3d4"
    assert sample.created_at == now
    assert sample.updated_at == now
    assert sample.name == "MacBook Pro M3"


def test_api_response_envelope_with_custom_message() -> None:
    """Verify ApiResponse envelope with custom message and schema payload."""
    now = datetime.now(timezone.utc)
    sample = SampleSchema(
        id="item_001",
        created_at=now,
        updated_at=now,
        name="Cotton T-Shirt",
    )

    response = ApiResponse[SampleSchema](data=sample, message="ok")

    # 1. Check data structure on Python object
    assert response.message == "ok"
    assert response.data.id == "item_001"
    assert response.data.name == "Cotton T-Shirt"

    # 2. Check dictionary dump (model_dump)
    response_dict = response.model_dump()
    assert response_dict["message"] == "ok"
    assert response_dict["data"]["id"] == "item_001"
    assert response_dict["data"]["name"] == "Cotton T-Shirt"

    # 3. Check JSON serialization (model_dump_json)
    json_str = response.model_dump_json()
    parsed_json = json.loads(json_str)

    assert parsed_json["message"] == "ok"
    assert parsed_json["data"]["id"] == "item_001"
    assert parsed_json["data"]["name"] == "Cotton T-Shirt"
    assert "created_at" in parsed_json["data"]
    assert "updated_at" in parsed_json["data"]


def test_api_response_envelope_default_message() -> None:
    """Verify ApiResponse envelope defaults to message='success'."""
    now = datetime.now(timezone.utc)
    sample = SampleSchema(
        id="item_002",
        created_at=now,
        updated_at=now,
        name="Mechanical Keyboard",
    )

    response = ApiResponse[SampleSchema](data=sample)
    assert response.message == "success"
    assert response.data.name == "Mechanical Keyboard"


def test_paginated_response_manual() -> None:
    """Verify PaginatedResponse when initialized directly with pagination fields."""
    now = datetime.now(timezone.utc)
    item1 = SampleSchema(id="1", created_at=now, updated_at=now, name="Product 1")
    item2 = SampleSchema(id="2", created_at=now, updated_at=now, name="Product 2")

    paginated = PaginatedResponse[SampleSchema](
        data=[item1, item2],
        total=10,
        page=1,
        page_size=2,
        has_next=True,
    )

    assert len(paginated.data) == 2
    assert paginated.total == 10
    assert paginated.page == 1
    assert paginated.page_size == 2
    assert paginated.has_next is True

    # Check JSON serialization
    dumped = paginated.model_dump()
    assert dumped["total"] == 10
    assert dumped["has_next"] is True
    assert len(dumped["data"]) == 2


def test_paginated_response_create_factory() -> None:
    """Verify PaginatedResponse.create factory method automatically calculates has_next."""
    now = datetime.now(timezone.utc)
    items = [
        SampleSchema(id="1", created_at=now, updated_at=now, name="Product 1"),
        SampleSchema(id="2", created_at=now, updated_at=now, name="Product 2"),
    ]

    # Page 1: page=1, page_size=2, total=5 -> (1 * 2) < 5 -> has_next = True
    page1 = PaginatedResponse.create(data=items, total=5, page=1, page_size=2)
    assert page1.has_next is True

    # Page 3: page=3, page_size=2, total=5 -> (3 * 2) < 5 -> has_next = False
    page3 = PaginatedResponse.create(data=[items[0]], total=5, page=3, page_size=2)
    assert page3.has_next is False


def test_error_response_serialization() -> None:
    """Verify ErrorResponse with detail message and machine-readable error_code."""
    # 1. ErrorResponse with detail only
    error1 = ErrorResponse(detail="Resource not found")
    assert error1.detail == "Resource not found"
    assert error1.error_code is None

    dumped1 = error1.model_dump()
    assert dumped1 == {"detail": "Resource not found", "error_code": None}

    # 2. ErrorResponse with error_code
    error2 = ErrorResponse(detail="Product slug already exists", error_code="DUPLICATE_SLUG")
    assert error2.detail == "Product slug already exists"
    assert error2.error_code == "DUPLICATE_SLUG"

    json_str = error2.model_dump_json()
    parsed = json.loads(json_str)
    assert parsed["detail"] == "Product slug already exists"
    assert parsed["error_code"] == "DUPLICATE_SLUG"

