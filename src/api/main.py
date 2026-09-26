"""FastAPI application entry-point."""

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from src.api.common.exception_handlers import register_exception_handlers
from src.api.common.middleware import RequestIDMiddleware, RequestLoggingMiddleware
from src.core.config import settings

app = FastAPI(
    title=settings.PROJECT_NAME,
    version=settings.API_VERSION,
)

# --- 1. Đăng ký Middleware Stack (Thứ tự: CORS -> RequestID -> Logging) ---
# CORS: Cho phép các trình duyệt / frontend gọi API an toàn
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.ALLOWED_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Request ID: Tự động gán mã định danh duy nhất X-Request-ID cho mọi yêu cầu
app.add_middleware(RequestIDMiddleware)

# Request Logging: Ghi log thời gian xử lý và mã trạng thái HTTP
app.add_middleware(RequestLoggingMiddleware)

# --- 2. Đăng ký các bộ xử lý lỗi toàn cục cho ứng dụng ---
register_exception_handlers(app)


@app.get("/health", tags=["System"])
async def health_check() -> dict:
    """Lightweight liveness probe."""
    return {"status": "healthy", "version": settings.API_VERSION}
