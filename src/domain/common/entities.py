"""Base domain entities — pure Python, zero framework dependencies."""

import uuid
from dataclasses import dataclass, field
from datetime import datetime, timezone


def _utc_now() -> datetime:
    """Return the current UTC-aware datetime."""
    return datetime.now(timezone.utc)


def _new_id() -> str:
    """Generate a new UUID v4 string."""
    return str(uuid.uuid4())


@dataclass
class BaseEntity:
    """Root entity that every domain model inherits from.

    Attributes:
        id: Universally unique identifier (UUID v4 string).
        created_at: UTC timestamp of creation.
        updated_at: UTC timestamp of the last modification.
    """

    id: str = field(default_factory=_new_id)
    created_at: datetime = field(default_factory=_utc_now)
    updated_at: datetime = field(default_factory=_utc_now)
