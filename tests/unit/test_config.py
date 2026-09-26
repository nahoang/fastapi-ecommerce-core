"""Unit tests for application configuration and settings.

Verifies that settings are properly loaded with correct data types,
particularly that financial configurations (TAX_RATE_PERCENT) strictly use Decimal
and defaults align with US standards (USD currency).
"""

from decimal import Decimal
import pytest
from src.core.config import Settings, settings


def test_settings_project_name() -> None:
    """Verify default project name is configured correctly."""
    # Check that PROJECT_NAME matches expected application name
    assert settings.PROJECT_NAME == "FastAPI E-Commerce Core"


def test_settings_tax_rate_is_decimal() -> None:
    """Verify US sales tax rate is strictly Decimal to avoid floating-point errors."""
    # 1. Check data type: must be Decimal
    assert isinstance(settings.TAX_RATE_PERCENT, Decimal), (
        f"TAX_RATE_PERCENT must be Decimal, got {type(settings.TAX_RATE_PERCENT)}"
    )

    # 2. Check default value: 8.0%
    assert settings.TAX_RATE_PERCENT == Decimal("8.0")


def test_settings_default_values() -> None:
    """Verify default settings values across categories follow US standards."""
    # Check debug flag and API version
    assert settings.DEBUG is True
    assert settings.API_VERSION == "0.1.0"

    # Check default database settings
    assert "sqlite+aiosqlite" in settings.DATABASE_URL
    assert settings.DATABASE_ECHO is True

    # Check security & authentication settings
    assert settings.SECRET_KEY == "change-me-in-production"
    assert settings.ACCESS_TOKEN_EXPIRE_MINUTES == 30

    # Check inventory reservation settings
    assert settings.RESERVATION_TTL_MINUTES == 15

    # Check default currency (US Dollar)
    assert settings.DEFAULT_CURRENCY == "USD"


def test_settings_custom_override() -> None:
    """Verify settings can be overridden and strings convert to Decimal properly."""
    # Instantiate custom settings with explicit parameters
    custom_settings = Settings(
        PROJECT_NAME="Custom E-Commerce",
        TAX_RATE_PERCENT="7.25",  # String "7.25" (e.g. California base sales tax) converted to Decimal
        DEFAULT_CURRENCY="USD",
    )

    # Verify overridden values
    assert custom_settings.PROJECT_NAME == "Custom E-Commerce"
    assert custom_settings.DEFAULT_CURRENCY == "USD"

    # Verify Pydantic converts string '7.25' to Decimal('7.25')
    assert isinstance(custom_settings.TAX_RATE_PERCENT, Decimal)
    assert custom_settings.TAX_RATE_PERCENT == Decimal("7.25")
