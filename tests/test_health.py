"""Test suite for system health endpoints."""

import pytest
from httpx import AsyncClient


async def test_health_check_returns_healthy(client: AsyncClient) -> None:
    """Verify that GET /health returns 200 OK with healthy status and correct version."""
    # 1. Send GET request to /health endpoint via test client
    response = await client.get("/health")

    # 2. Assert HTTP response status code is 200 OK
    assert response.status_code == 200

    # 3. Assert response JSON matches expected payload
    data = response.json()
    assert data["status"] == "healthy"
    assert data["version"] == "0.1.0"
