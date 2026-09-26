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
    # 1. Send GET /health request without X-Request-ID header
    response = await client.get("/health")

    # 2. Verify successful response status code
    assert response.status_code == 200

    # 3. Retrieve X-Request-ID from response headers
    request_id = response.headers.get("X-Request-ID")
    assert request_id is not None, "Response header X-Request-ID must be present"

    # 4. Verify ID format is valid uuid4.hex (32 characters: lowercase 0-9, a-f)
    assert len(request_id) == 32
    assert HEX_32_PATTERN.match(request_id) is not None, f"Expected 32 hex chars, got {request_id}"


async def test_request_id_preserved_when_provided_by_client(client: AsyncClient) -> None:
    """Verify that an existing client-provided X-Request-ID is preserved and echoed back."""
    # 1. Prepare custom request ID from client
    custom_trace_id = "trace-client-abc-12345"

    # 2. Send request with custom X-Request-ID header
    response = await client.get("/health", headers={"X-Request-ID": custom_trace_id})

    # 3. Verify successful status code
    assert response.status_code == 200

    # 4. Verify returned header strictly matches the client-supplied ID
    assert response.headers.get("X-Request-ID") == custom_trace_id


async def test_request_logging_records_transaction(
    client: AsyncClient,
    caplog: pytest.LogCaptureFixture,
) -> None:
    """Verify that RequestLoggingMiddleware records the request details to Python logger."""
    # 1. Enable log capture at INFO level for src.api.common.middleware
    caplog.set_level(logging.INFO)

    # 2. Send request with custom X-Request-ID
    custom_id = "test-log-trace-id-999"
    response = await client.get("/health", headers={"X-Request-ID": custom_id})
    assert response.status_code == 200

    # 3. Verify log message matches standard format:
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
    # 1. Simulate request from frontend at localhost:3000
    origin = "http://localhost:3000"
    response = await client.get("/health", headers={"Origin": origin})

    # 2. Verify successful status code
    assert response.status_code == 200

    # 3. Verify CORS response headers based on config (allow_origins, allow_credentials)
    assert response.headers.get("access-control-allow-origin") == origin
    assert response.headers.get("access-control-allow-credentials") == "true"


async def test_cors_preflight_options_request(client: AsyncClient) -> None:
    """Verify that CORSMiddleware responds properly to HTTP OPTIONS preflight checks."""
    # 1. Simulate browser preflight OPTIONS request
    origin = "http://localhost:3000"
    response = await client.options(
        "/health",
        headers={
            "Origin": origin,
            "Access-Control-Request-Method": "GET",
            "Access-Control-Request-Headers": "X-Request-ID, Content-Type",
        },
    )

    # 2. Verify status code 200 for preflight response
    assert response.status_code == 200

    # 3. Verify CORS allow origin header is returned
    assert response.headers.get("access-control-allow-origin") == origin

