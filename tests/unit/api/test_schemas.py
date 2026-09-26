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
    """Schema thử nghiệm kế thừa từ BaseResponseSchema."""

    name: str


@dataclass
class MockDomainEntity:
    """Mock đối tượng Python mô phỏng Domain Entity hoặc ORM Model có các thuộc tính."""

    id: str
    created_at: datetime
    updated_at: datetime
    name: str


def test_base_schema_from_attributes() -> None:
    """Kiểm tra BaseSchema cho phép đọc dữ liệu trực tiếp từ thuộc tính object (from_attributes=True)."""
    now = datetime.now(timezone.utc)
    mock_entity = MockDomainEntity(
        id="a1b2c3d4e5f6a1b2c3d4e5f6a1b2c3d4",
        created_at=now,
        updated_at=now,
        name="MacBook Pro M3",
    )

    # Sử dụng model_validate để convert từ object sang Pydantic schema
    sample = SampleSchema.model_validate(mock_entity)

    assert sample.id == "a1b2c3d4e5f6a1b2c3d4e5f6a1b2c3d4"
    assert sample.created_at == now
    assert sample.updated_at == now
    assert sample.name == "MacBook Pro M3"


def test_api_response_envelope_with_custom_message() -> None:
    """Kiểm tra ApiResponse envelope với thông điệp tùy chỉnh và schema payload."""
    now = datetime.now(timezone.utc)
    sample = SampleSchema(
        id="item_001",
        created_at=now,
        updated_at=now,
        name="Áo thun cotton",
    )

    response = ApiResponse[SampleSchema](data=sample, message="ok")

    # 1. Kiểm tra cấu trúc dữ liệu trên Python object
    assert response.message == "ok"
    assert response.data.id == "item_001"
    assert response.data.name == "Áo thun cotton"

    # 2. Kiểm tra xuất ra dictionary (model_dump)
    response_dict = response.model_dump()
    assert response_dict["message"] == "ok"
    assert response_dict["data"]["id"] == "item_001"
    assert response_dict["data"]["name"] == "Áo thun cotton"

    # 3. Kiểm tra xuất ra chuỗi JSON hợp lệ (model_dump_json)
    json_str = response.model_dump_json()
    parsed_json = json.loads(json_str)

    assert parsed_json["message"] == "ok"
    assert parsed_json["data"]["id"] == "item_001"
    assert parsed_json["data"]["name"] == "Áo thun cotton"
    assert "created_at" in parsed_json["data"]
    assert "updated_at" in parsed_json["data"]


def test_api_response_envelope_default_message() -> None:
    """Kiểm tra ApiResponse envelope có giá trị mặc định cho message là 'success'."""
    now = datetime.now(timezone.utc)
    sample = SampleSchema(
        id="item_002",
        created_at=now,
        updated_at=now,
        name="Bàn phím cơ",
    )

    response = ApiResponse[SampleSchema](data=sample)
    assert response.message == "success"
    assert response.data.name == "Bàn phím cơ"


def test_paginated_response_manual() -> None:
    """Kiểm tra PaginatedResponse khi khởi tạo trực tiếp với các trường phân trang."""
    now = datetime.now(timezone.utc)
    item1 = SampleSchema(id="1", created_at=now, updated_at=now, name="Sản phẩm 1")
    item2 = SampleSchema(id="2", created_at=now, updated_at=now, name="Sản phẩm 2")

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

    # Kiểm tra serialization sang JSON
    dumped = paginated.model_dump()
    assert dumped["total"] == 10
    assert dumped["has_next"] is True
    assert len(dumped["data"]) == 2


def test_paginated_response_create_factory() -> None:
    """Kiểm tra hàm tiện ích PaginatedResponse.create tự động tính toán has_next."""
    now = datetime.now(timezone.utc)
    items = [
        SampleSchema(id="1", created_at=now, updated_at=now, name="Sản phẩm 1"),
        SampleSchema(id="2", created_at=now, updated_at=now, name="Sản phẩm 2"),
    ]

    # Trang 1: page=1, page_size=2, total=5 -> (1 * 2) < 5 -> has_next = True
    page1 = PaginatedResponse.create(data=items, total=5, page=1, page_size=2)
    assert page1.has_next is True

    # Trang 3: page=3, page_size=2, total=5 -> (3 * 2) < 5 -> has_next = False
    page3 = PaginatedResponse.create(data=[items[0]], total=5, page=3, page_size=2)
    assert page3.has_next is False


def test_error_response_serialization() -> None:
    """Kiểm tra ErrorResponse với thông báo chi tiết và mã lỗi định danh."""
    # 1. ErrorResponse chỉ có detail
    error1 = ErrorResponse(detail="Resource not found")
    assert error1.detail == "Resource not found"
    assert error1.error_code is None

    dumped1 = error1.model_dump()
    assert dumped1 == {"detail": "Resource not found", "error_code": None}

    # 2. ErrorResponse có error_code
    error2 = ErrorResponse(detail="Product slug already exists", error_code="DUPLICATE_SLUG")
    assert error2.detail == "Product slug already exists"
    assert error2.error_code == "DUPLICATE_SLUG"

    json_str = error2.model_dump_json()
    parsed = json.loads(json_str)
    assert parsed["detail"] == "Product slug already exists"
    assert parsed["error_code"] == "DUPLICATE_SLUG"
