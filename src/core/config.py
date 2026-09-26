"""Application settings and environment variable configuration.

Uses pydantic-settings to validate and parse configuration values from environment variables or .env file.
"""

from decimal import Decimal
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Core settings for the FastAPI E-Commerce application.

    All properties provide sensible defaults for local development following US standards and English conventions.
    In production environments, sensitive values (such as SECRET_KEY) must be provided via environment variables.
    """

    # --- 1. Project & Application Meta ---
    # Project title displayed in Swagger UI and OpenAPI documentation
    PROJECT_NAME: str = "FastAPI E-Commerce Core"
    # Debug mode flag: set to False in production
    DEBUG: bool = True
    # API version string following Semantic Versioning
    API_VERSION: str = "0.1.0"

    # --- 2. Database Connection ---
    # Async database URL (SQLite async by default for local development)
    DATABASE_URL: str = "sqlite+aiosqlite:///./ecommerce.db"
    # Log raw SQL statements to the terminal to inspect ORM query behavior
    DATABASE_ECHO: bool = True

    # --- 3. Security & CORS ---
    # Allowed origins for Cross-Origin Resource Sharing (CORS)
    # Default ["*"] allows all origins during local development; restricted in production
    ALLOWED_ORIGINS: list[str] = ["*"]
    # Secret key used for signing and verifying JWT tokens
    SECRET_KEY: str = "change-me-in-production"
    # Expiration time for access tokens in minutes
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 30

    # --- 4. Inventory & Cart Reservation ---
    # Time in minutes an item is held reserved in a cart before being released back to inventory
    RESERVATION_TTL_MINUTES: int = 15

    # --- 5. Financial & US Localization Defaults ---
    # Default currency code (ISO 4217 - US Dollar)
    DEFAULT_CURRENCY: str = "USD"
    # Default US sales tax percentage: strictly Decimal to prevent floating-point rounding errors
    TAX_RATE_PERCENT: Decimal = Decimal("8.0")

    # Load environment variables from .env file if present, ignoring extra undeclared variables
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")


# Global singleton instance for access across application modules
settings = Settings()
