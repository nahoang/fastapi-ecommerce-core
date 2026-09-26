"""FastAPI application entry-point."""

from fastapi import FastAPI

from src.api.common.exception_handlers import register_exception_handlers

app = FastAPI(
    title="FastAPI E-Commerce Core",
    version="0.1.0",
)

# Đăng ký các bộ xử lý lỗi toàn cục cho ứng dụng
register_exception_handlers(app)


@app.get("/health", tags=["System"])
async def health_check() -> dict:
    """Lightweight liveness probe."""
    return {"status": "healthy", "version": "0.1.0"}
