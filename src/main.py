"""Root entrypoint re-exporting FastAPI app from src.api.main."""

from src.api.main import app

__all__ = ["app"]
