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

# --- 1. Register Middleware Stack (Order: CORS -> RequestID -> Logging) ---
# CORS: Allows frontend clients / browsers to call the API safely
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.ALLOWED_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Request ID: Automatically injects a unique X-Request-ID correlation header
app.add_middleware(RequestIDMiddleware)

# Request Logging: Logs response duration and HTTP status codes
app.add_middleware(RequestLoggingMiddleware)

# --- 2. Register Global Exception Handlers ---
register_exception_handlers(app)



@app.get("/health", tags=["System"])
async def health_check() -> dict:
    """Lightweight liveness probe."""
    return {"status": "healthy", "version": settings.API_VERSION}
