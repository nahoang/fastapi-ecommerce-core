"""Unit tests for TimestampMixin and database base models."""

import pytest
from sqlalchemy import String, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import Mapped, mapped_column

from src.core.database import Base
from src.domain.common.entities import BaseEntity
from src.infrastructure.database.base_model import TimestampMixin


class SampleModel(TimestampMixin, Base):
    """Test model inheriting TimestampMixin and DeclarativeBase."""

    __tablename__ = "sample"

    name: Mapped[str] = mapped_column(String(100), nullable=False)


@pytest.mark.asyncio
async def test_timestamp_mixin_auto_generates_id_and_timestamps(
    db_session: AsyncSession,
) -> None:
    """Verify that TimestampMixin automatically generates a 32-character hex UUID and timestamps."""
    # 1. Create a new sample record without specifying id or timestamps
    sample = SampleModel(name="Sample Test Product")
    db_session.add(sample)
    await db_session.commit()
    await db_session.refresh(sample)

    # 2. Check auto-generated primary key ID
    assert sample.id is not None
    assert isinstance(sample.id, str)
    assert len(sample.id) == 32
    # Verify that id contains only valid hexadecimal characters
    int(sample.id, 16)

    # 3. Check created_at and updated_at timestamps
    assert sample.created_at is not None
    assert sample.updated_at is not None


@pytest.mark.asyncio
async def test_timestamp_mixin_custom_id(
    db_session: AsyncSession,
) -> None:
    """Verify that a manually provided ID is preserved and not overwritten."""
    custom_id = "a" * 32
    sample = SampleModel(id=custom_id, name="Custom ID Item")
    db_session.add(sample)
    await db_session.commit()
    await db_session.refresh(sample)

    assert sample.id == custom_id
    assert sample.created_at is not None


@pytest.mark.asyncio
async def test_base_entity_domain_isolation() -> None:
    """Verify that BaseEntity is a pure Python dataclass with 32-char hex ID and optional timestamps."""
    # 1. Default instantiation
    entity = BaseEntity()
    assert entity.id is not None
    assert isinstance(entity.id, str)
    assert len(entity.id) == 32
    int(entity.id, 16)
    assert entity.created_at is None
    assert entity.updated_at is None

    # 2. Instantiation with custom ID
    custom_entity = BaseEntity(id="custom_id_123")
    assert custom_entity.id == "custom_id_123"

    # 3. Verify BaseEntity has NO SQLAlchemy declarative attributes
    assert not hasattr(entity, "__tablename__")
    assert not hasattr(entity, "_sa_class_manager")
