"""Base domain entities — pure Python, zero framework dependencies."""

import uuid
from dataclasses import dataclass, field
from datetime import datetime


def _new_id() -> str:
    """Generate a random 32-character hexadecimal UUID v4 string.

    Returns:
        A 32-character lowercase hex string without hyphens.
    """
    return uuid.uuid4().hex


@dataclass
class BaseEntity:
    """Root entity that every domain model inherits from.

    This is a pure Python dataclass with zero database or framework dependencies,
    strictly adhering to Clean Architecture domain layer isolation.

    Attributes:
        id: Universally unique identifier (UUID v4 32-character hex string).
        created_at: UTC timestamp of creation (None before persistence).
        updated_at: UTC timestamp of last modification (None before persistence).
    """

    id: str = field(default_factory=_new_id)
    created_at: datetime | None = None
    updated_at: datetime | None = None
