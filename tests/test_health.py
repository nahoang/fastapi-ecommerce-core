"""Test suite for system health endpoints."""

import pytest
from httpx import AsyncClient


async def test_health_check_returns_healthy(client: AsyncClient) -> None:
    """Verify that GET /health returns 200 OK with healthy status and correct version."""
    # 1. Gửi request GET tới endpoint /health thông qua test client
    response = await client.get("/health")

    # 2. Kiểm tra mã trạng thái HTTP trả về phải là 200 OK
    assert response.status_code == 200

    # 3. Kiểm tra nội dung JSON trả về khớp với dữ liệu dự kiến
    data = response.json()
    assert data["status"] == "healthy"
    assert data["version"] == "0.1.0"
