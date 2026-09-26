"""Unit tests for IRepository interface and BaseRepository SQLAlchemy 2.0 implementation."""

import pytest
from sqlalchemy import Integer, String
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import Mapped, mapped_column

from src.application.common.repository import IRepository
from src.core.database import Base
from src.infrastructure.database.base_model import TimestampMixin
from src.infrastructure.database.base_repository import BaseRepository


class SampleModel(TimestampMixin, Base):
    """Declarative ORM model used to verify BaseRepository operations."""

    __tablename__ = "test_sample_repository_items"

    name: Mapped[str] = mapped_column(String(100), nullable=False)
    price: Mapped[int] = mapped_column(Integer, default=0, nullable=False)


class SampleRepository(BaseRepository[SampleModel]):
    """Concrete repository implementation binding SampleModel to BaseRepository."""

    def __init__(self, session: AsyncSession) -> None:
        super().__init__(session=session, model_class=SampleModel)


@pytest.mark.asyncio
async def test_repository_crud_lifecycle(db_session: AsyncSession) -> None:
    """Test full CRUD lifecycle: add -> get_by_id -> update -> list_all -> delete."""
    repo = SampleRepository(session=db_session)

    # 0. Verify repository satisfies both the concrete and abstract interface types
    assert isinstance(repo, IRepository)
    assert isinstance(repo, BaseRepository)

    # 1. CREATE (add): Persist a new entity
    item1 = SampleModel(name="Mechanical Keyboard", price=120)
    created_item1 = await repo.add(item1)

    assert created_item1.id is not None
    assert len(created_item1.id) == 32
    assert created_item1.name == "Mechanical Keyboard"
    assert created_item1.price == 120
    assert created_item1.created_at is not None
    assert created_item1.updated_at is not None

    # 2. READ (get_by_id): Retrieve by primary key id
    fetched_item = await repo.get_by_id(created_item1.id)
    assert fetched_item is not None
    assert fetched_item.id == created_item1.id
    assert fetched_item.name == "Mechanical Keyboard"
    assert fetched_item.price == 120

    # 3. UPDATE: Modify attributes and persist changes via merge/flush
    fetched_item.name = "Custom Wireless Keyboard"
    fetched_item.price = 150
    updated_item = await repo.update(fetched_item)

    assert updated_item.id == created_item1.id
    assert updated_item.name == "Custom Wireless Keyboard"
    assert updated_item.price == 150

    # Verify update persisted in database session
    re_fetched = await repo.get_by_id(created_item1.id)
    assert re_fetched is not None
    assert re_fetched.name == "Custom Wireless Keyboard"
    assert re_fetched.price == 150

    # 4. LIST (list_all): Add a second record and test pagination
    item2 = SampleModel(name="Gaming Mouse", price=60)
    created_item2 = await repo.add(item2)

    # Fetch all records
    all_items = await repo.list_all(limit=10, offset=0)
    assert len(all_items) == 2
    item_ids = [item.id for item in all_items]
    assert created_item1.id in item_ids
    assert created_item2.id in item_ids

    # Pagination test: limit 1, offset 0 -> 1 record
    page_1 = await repo.list_all(limit=1, offset=0)
    assert len(page_1) == 1

    # Pagination test: limit 1, offset 1 -> 1 record (different item)
    page_2 = await repo.list_all(limit=1, offset=1)
    assert len(page_2) == 1
    assert page_1[0].id != page_2[0].id

    # 5. DELETE: Remove the first record by id
    await repo.delete(created_item1.id)

    # Verify item is deleted and get_by_id returns None
    assert await repo.get_by_id(created_item1.id) is None

    # Verify remaining records
    remaining = await repo.list_all(limit=10, offset=0)
    assert len(remaining) == 1
    assert remaining[0].id == created_item2.id


@pytest.mark.asyncio
async def test_get_by_id_nonexistent_returns_none(db_session: AsyncSession) -> None:
    """Verify get_by_id returns None when queried with a non-existent id."""
    repo = SampleRepository(session=db_session)
    non_existent_id = "0" * 32

    result = await repo.get_by_id(non_existent_id)
    assert result is None


@pytest.mark.asyncio
async def test_delete_nonexistent_entity_is_safe_noop(db_session: AsyncSession) -> None:
    """Verify delete executes safely without raising exceptions when entity does not exist."""
    repo = SampleRepository(session=db_session)
    non_existent_id = "f" * 32

    # Should execute smoothly without throwing errors
    await repo.delete(non_existent_id)
    assert await repo.get_by_id(non_existent_id) is None


@pytest.mark.asyncio
async def test_repository_flush_allows_caller_rollback(db_session: AsyncSession) -> None:
    """Verify that BaseRepository flushes without committing, allowing caller-managed transaction control."""
    repo = SampleRepository(session=db_session)

    # 1. Add item via repository (invokes flush() internally)
    item = SampleModel(name="Temporary Uncommitted Item", price=999)
    await repo.add(item)

    # Entity has received its server defaults during flush()
    assert item.id is not None

    # Item is visible in current session
    assert await repo.get_by_id(item.id) is not None

    # 2. Caller issues a rollback on the outer transaction boundary
    await db_session.rollback()

    # 3. Item must not exist after rollback, proving BaseRepository did not prematurely commit
    assert await repo.get_by_id(item.id) is None
