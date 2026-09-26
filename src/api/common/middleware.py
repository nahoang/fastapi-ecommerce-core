"""HTTP Middlewares for FastAPI E-Commerce Core.

Middlewares act as checkpoints (interceptors) for incoming HTTP requests and outgoing HTTP responses:
1. RequestIDMiddleware: Ensures every request has a unique correlation ID (X-Request-ID) for tracing.
2. RequestLoggingMiddleware: Measures response time and logs HTTP transactions using Python's logging module.
"""

import logging
import time
from uuid import uuid4

from starlette.middleware.base import BaseHTTPMiddleware, RequestResponseEndpoint
from starlette.requests import Request
from starlette.responses import Response

# Create standard Python logger for the current module ("src.api.common.middleware")
logger = logging.getLogger(__name__)


class RequestIDMiddleware(BaseHTTPMiddleware):
    """Middleware that injects a unique correlation ID (Request ID) for every HTTP request.

    Why correlation IDs matter:
    - In high-throughput systems, a unique request ID allows tracing a request's entire
      lifecycle across multiple architecture layers (Controller -> Service -> DB -> External APIs).
    - If the client (frontend/mobile) supplies an "X-Request-ID" header, we reuse it.
    - If missing, we generate a fresh random 32-character hex UUID v4.
    """

    async def dispatch(self, request: Request, call_next: RequestResponseEndpoint) -> Response:
        # Step 1: Check if client provided X-Request-ID header, otherwise generate a new UUID4
        request_id = request.headers.get("X-Request-ID") or uuid4().hex

        # Step 2: Store request_id in request.state so downstream handlers and middlewares can access it
        request.state.request_id = request_id

        # Step 3: Forward the request to the next middleware or route handler
        response = await call_next(request)

        # Step 4: Attach X-Request-ID to response headers for client tracking
        response.headers["X-Request-ID"] = request_id

        return response


class RequestLoggingMiddleware(BaseHTTPMiddleware):
    """Middleware that logs HTTP transaction details and measures execution duration.

    Log format:
        {method} {path} → {status_code} in {duration_ms:.2f}ms [{request_id}]

    Why time.perf_counter()?
    - time.perf_counter() is a high-resolution monotonic clock in Python, unaffected by
      system clock updates (such as automatic NTP synchronization).
    """

    async def dispatch(self, request: Request, call_next: RequestResponseEndpoint) -> Response:
        # Step 1: Record processing start timestamp
        start_time = time.perf_counter()

        # Step 2: Process request through the rest of the application
        try:
            response = await call_next(request)
        except Exception:
            # If an unhandled exception occurs, calculate duration and log 500 before re-raising
            duration_ms = (time.perf_counter() - start_time) * 1000
            request_id = getattr(request.state, "request_id", "unknown")
            logger.error(
                f"{request.method} {request.url.path} → 500 in {duration_ms:.2f}ms [{request_id}]"
            )
            raise

        # Step 3: Compute total elapsed duration in milliseconds
        duration_ms = (time.perf_counter() - start_time) * 1000

        # Step 4: Extract request_id from state or response headers
        request_id = (
            getattr(request.state, "request_id", None)
            or response.headers.get("X-Request-ID")
            or "unknown"
        )

        # Step 5: Log at INFO level with standard format: {method} {path} → {status_code} in {duration_ms}ms [{request_id}]
        logger.info(
            f"{request.method} {request.url.path} → {response.status_code} in {duration_ms:.2f}ms [{request_id}]"
        )

        return response

