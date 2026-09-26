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

# Tạo standard Python logger có tên tương ứng với module hiện tại ("src.api.common.middleware")
logger = logging.getLogger(__name__)


class RequestIDMiddleware(BaseHTTPMiddleware):
    """Middleware tự động gắn mã định danh duy nhất (Request ID) cho từng HTTP request.
    
    Tại sao cần Request ID?
    - Khi có hàng nghìn yêu cầu gửi tới server cùng lúc, việc gán ID duy nhất giúp theo vết (trace)
      toàn bộ vòng đời của một request qua nhiều tầng (Controller -> Service -> Database -> External APIs).
    - Nếu client (frontend/mobile) đã gửi header "X-Request-ID", ta tái sử dụng ID đó.
    - Nếu client chưa gửi, ta sinh mới một UUID v4 dạng hex 32 ký tự ngẫu nhiên.
    """

    async def dispatch(self, request: Request, call_next: RequestResponseEndpoint) -> Response:
        # Bước 1: Kiểm tra xem client có gửi header X-Request-ID không, nếu không thì sinh UUID4 mới
        request_id = request.headers.get("X-Request-ID") or uuid4().hex

        # Bước 2: Lưu request_id vào request.state để các middleware hoặc handler phía sau có thể truy cập
        request.state.request_id = request_id

        # Bước 3: Chuyển request đến tầng tiếp theo trong chuỗi middleware / API endpoint
        response = await call_next(request)

        # Bước 4: Gắn X-Request-ID vào response headers để client biết mã định danh của phiên xử lý
        response.headers["X-Request-ID"] = request_id

        return response


class RequestLoggingMiddleware(BaseHTTPMiddleware):
    """Middleware ghi log thông tin mỗi HTTP request và đo lường thời gian thực thi (duration).
    
    Định dạng log:
        {method} {path} → {status_code} in {duration_ms:.2f}ms [{request_id}]
    
    Tại sao dùng time.perf_counter()?
    - time.perf_counter() là đồng hồ đơn điệu (monotonic) có độ chính xác cao nhất trong Python,
      không bị ảnh hưởng khi đồng hồ hệ điều hành thay đổi (ví dụ: tự động đồng bộ giờ NTP).
    """

    async def dispatch(self, request: Request, call_next: RequestResponseEndpoint) -> Response:
        # Bước 1: Ghi nhận thời điểm bắt đầu xử lý request
        start_time = time.perf_counter()

        # Bước 2: Cho phép request đi qua các middleware khác và thực thi endpoint
        try:
            response = await call_next(request)
        except Exception:
            # Nếu xảy ra ngoại lệ chưa được xử lý, đo thời gian và log lỗi 500 trước khi ném lại ngoại lệ
            duration_ms = (time.perf_counter() - start_time) * 1000
            request_id = getattr(request.state, "request_id", "unknown")
            logger.error(
                f"{request.method} {request.url.path} → 500 in {duration_ms:.2f}ms [{request_id}]"
            )
            raise

        # Bước 3: Tính toán khoảng thời gian xử lý ra mili-giây (ms)
        duration_ms = (time.perf_counter() - start_time) * 1000

        # Bước 4: Lấy request_id từ request.state (hoặc từ response header nếu đã được gắn)
        request_id = (
            getattr(request.state, "request_id", None)
            or response.headers.get("X-Request-ID")
            or "unknown"
        )

        # Bước 5: Ghi log ở mức INFO theo định dạng chuẩn: {method} {path} → {status_code} in {duration_ms}ms [{request_id}]
        logger.info(
            f"{request.method} {request.url.path} → {response.status_code} in {duration_ms:.2f}ms [{request_id}]"
        )

        return response
