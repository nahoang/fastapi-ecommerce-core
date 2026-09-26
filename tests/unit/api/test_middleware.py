"""Unit tests for API Middlewares (Request ID, Logging, and CORS).

Verifies the HTTP middleware stack behavior:
1. RequestIDMiddleware generates a 32-character hexadecimal UUID if none is supplied.
2. RequestIDMiddleware preserves and returns any custom X-Request-ID provided by the client.
3. RequestLoggingMiddleware logs request method, path, HTTP status, and duration in ms.
4. CORSMiddleware responds with appropriate Cross-Origin headers for client applications.
"""

import logging
import re
import pytest
from httpx import AsyncClient


HEX_32_PATTERN = re.compile(r"^[0-9a-f]{32}$")


async def test_request_id_generated_automatically(client: AsyncClient) -> None:
    """Verify that a request without X-Request-ID receives a newly generated 32-character hex ID."""
    # 1. Gửi request GET /health không truyền header X-Request-ID
    response = await client.get("/health")

    # 2. Kiểm tra response status code thành công
    assert response.status_code == 200

    # 3. Lấy X-Request-ID từ response headers
    request_id = response.headers.get("X-Request-ID")
    assert request_id is not None, "Response header X-Request-ID must be present"

    # 4. Kiểm tra ID có đúng định dạng uuid4.hex (32 ký tự số và chữ thường từ 0-9, a-f)
    assert len(request_id) == 32
    assert HEX_32_PATTERN.match(request_id) is not None, f"Expected 32 hex chars, got {request_id}"


async def test_request_id_preserved_when_provided_by_client(client: AsyncClient) -> None:
    """Verify that an existing client-provided X-Request-ID is preserved and echoed back."""
    # 1. Chuẩn bị custom request ID từ phía client
    custom_trace_id = "trace-client-abc-12345"

    # 2. Gửi request kèm header X-Request-ID tự định nghĩa
    response = await client.get("/health", headers={"X-Request-ID": custom_trace_id})

    # 3. Kiểm tra status code thành công
    assert response.status_code == 200

    # 4. Kiểm tra header trả về trùng khớp hoàn toàn với ID client đã gửi
    assert response.headers.get("X-Request-ID") == custom_trace_id


async def test_request_logging_records_transaction(
    client: AsyncClient,
    caplog: pytest.LogCaptureFixture,
) -> None:
    """Verify that RequestLoggingMiddleware records the request details to Python logger."""
    # 1. Bật log capture ở mức INFO cho module src.api.common.middleware
    caplog.set_level(logging.INFO)

    # 2. Gửi request có kèm custom X-Request-ID
    custom_id = "test-log-trace-id-999"
    response = await client.get("/health", headers={"X-Request-ID": custom_id})
    assert response.status_code == 200

    # 3. Kiểm tra thông điệp log ghi nhận đúng format:
    # "{method} {path} → {status_code} in {duration_ms}ms [{request_id}]"
    expected_fragment = f"GET /health → 200 in"
    matching_records = [
        record for record in caplog.records
        if expected_fragment in record.message and custom_id in record.message
    ]

    assert len(matching_records) >= 1, (
        f"Expected log containing '{expected_fragment}' and '[{custom_id}]', "
        f"but got logs: {[r.message for r in caplog.records]}"
    )


async def test_cors_headers_with_origin(client: AsyncClient) -> None:
    """Verify that CORSMiddleware returns correct Access-Control headers when Origin is present."""
    # 1. Giả lập request từ frontend chạy ở localhost:3000
    origin = "http://localhost:3000"
    response = await client.get("/health", headers={"Origin": origin})

    # 2. Kiểm tra status code thành công
    assert response.status_code == 200

    # 3. Kiểm tra các header CORS theo cấu hình (allow_origins, allow_credentials)
    assert response.headers.get("access-control-allow-origin") == origin
    assert response.headers.get("access-control-allow-credentials") == "true"


async def test_cors_preflight_options_request(client: AsyncClient) -> None:
    """Verify that CORSMiddleware responds properly to HTTP OPTIONS preflight checks."""
    # 1. Giả lập trình duyệt gửi OPTIONS preflight check
    origin = "http://localhost:3000"
    response = await client.options(
        "/health",
        headers={
            "Origin": origin,
            "Access-Control-Request-Method": "GET",
            "Access-Control-Request-Headers": "X-Request-ID, Content-Type",
        },
    )

    # 2. Kiểm tra status code 200 cho preflight check
    assert response.status_code == 200

    # 3. Kiểm tra phản hồi header CORS cho phép origin
    assert response.headers.get("access-control-allow-origin") == origin
