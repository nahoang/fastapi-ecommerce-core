"""Base schemas and response envelopes for the API layer.

This module defines standardized Pydantic v2 models for API requests,
responses, generic envelopes, pagination, and error representations.
These schemas act as Data Transfer Objects (DTOs) between the HTTP API
and the internal application/domain layers.
"""

from datetime import datetime
from typing import Generic, TypeVar
from pydantic import BaseModel, ConfigDict

# TypeVar 'T' đại diện cho kiểu dữ liệu bất kỳ được bọc bên trong ApiResponse hoặc PaginatedResponse
# (Generic Type: giống như một chiếc hộp đa năng có thể chứa bất kỳ món đồ nào bên trong)
T = TypeVar("T")


class BaseSchema(BaseModel):
    """Lớp Schema cơ sở cho tất cả DTOs trong tầng API.

    from_attributes=True (thay thế orm_mode=True của Pydantic v1) cho phép
    Pydantic tự động đọc dữ liệu từ các thuộc tính của đối tượng (object.attribute)
    thay vì chỉ đọc từ dictionary (dict['key']), giúp serialize trực tiếp từ
    SQLAlchemy ORM model hoặc Domain Entity.
    """

    model_config = ConfigDict(from_attributes=True)


class BaseResponseSchema(BaseSchema):
    """Lớp Schema phản hồi cơ sở chứa các trường định danh và dấu thời gian kiểm toán.

    Attributes:
        id: Khóa chính dạng chuỗi UUID (32 ký tự hex).
        created_at: Thời điểm tạo bản ghi (UTC).
        updated_at: Thời điểm cập nhật bản ghi gần nhất (UTC).
    """

    id: str
    created_at: datetime
    updated_at: datetime


class ApiResponse(BaseModel, Generic[T]):
    """Vỏ bọc (Envelope) phản hồi API chuẩn hóa cho phản hồi đơn hoặc dữ liệu tùy biến.

    Quy chuẩn vỏ bọc giúp client (frontend/mobile) luôn nhận cấu trúc phản hồi
    đồng nhất dạng: { "data": ..., "message": "success" }.

    Attributes:
        data: Dữ liệu tải trọng chính (payload) có kiểu generic T.
        message: Thông điệp phản hồi (mặc định là 'success').
    """

    model_config = ConfigDict(from_attributes=True)

    data: T
    message: str = "success"


class PaginatedResponse(BaseModel, Generic[T]):
    """Vỏ bọc phản hồi API phân trang chuẩn hóa cho danh sách các bản ghi.

    Attributes:
        data: Danh sách các phần tử thuộc kiểu generic T trong trang hiện tại.
        total: Tổng số lượng bản ghi thỏa mãn điều kiện tìm kiếm.
        page: Số thứ tự trang hiện tại (bắt đầu từ 1).
        page_size: Số lượng bản ghi tối đa trên một trang.
        has_next: Cờ boolean cho biết còn trang kế tiếp hay không.
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
        """Hàm tiện ích (Factory method) tự động tính toán has_next dựa trên page và page_size.

        Args:
            data: Danh sách phần tử trong trang hiện tại.
            total: Tổng số bản ghi trong cơ sở dữ liệu.
            page: Trang hiện tại (1-indexed).
            page_size: Số phần tử trên mỗi trang.

        Returns:
            Đối tượng PaginatedResponse với has_next được tính toán tự động.
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
    """Cấu trúc phản hồi lỗi chuẩn hóa cho toàn hệ thống API.

    Attributes:
        detail: Mô tả chi tiết nguyên nhân lỗi trả về cho client.
        error_code: Mã định danh lỗi máy đọc (ví dụ: 'NOT_FOUND', 'VALIDATION_ERROR').
    """

    model_config = ConfigDict(from_attributes=True)

    detail: str
    error_code: str | None = None
