"""Base ORM model and mixins for infrastructure database layer.

This module defines reusable SQLAlchemy 2.0 mixins for database models,
providing standardized primary keys and automated UTC audit timestamps.
"""

import uuid
from datetime import datetime
from sqlalchemy import DateTime, String, func
from sqlalchemy.orm import Mapped, mapped_column


def _generate_uuid() -> str:
    """Generate a random 32-character hexadecimal UUID v4 string.

    Returns:
        A 32-character lowercase hex string (e.g. 'c9a646d306da4eea80b307b503760e10').
    """
    return uuid.uuid4().hex


class TimestampMixin:
    """SQLAlchemy 2.0 declarative mixin that provides common identity and audit timestamp fields.

    Attributes:
        id: 32-character hexadecimal UUID v4 primary key string.
        created_at: Non-nullable UTC timestamp automatically set on record creation by database server.
        updated_at: Non-nullable UTC timestamp automatically updated on record modification by database server.
    """

    # Primary key column storing a compact 32-character hex UUID
    id: Mapped[str] = mapped_column(
        String(32),
        primary_key=True,
        default=_generate_uuid,
    )

    # Server-side timestamp set automatically when the row is first inserted
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )

    # Server-side timestamp set initially and updated on every subsequent SQL UPDATE
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
    )
