"""FastAPI application entry-point."""

from fastapi import FastAPI

app = FastAPI(
    title="Codoric FastAPI E-Commerce Core",
    version="0.1.0",
)


@app.get("/health", tags=["System"])
async def health_check() -> dict:
    """Lightweight liveness probe."""
    return {"status": "healthy", "version": "0.1.0"}
