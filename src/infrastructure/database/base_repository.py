"""SQLAlchemy 2.0 Base Repository implementation for infrastructure layer.

This module provides the generic database repository implementation (BaseRepository)
that fulfills the IRepository interface contract using SQLAlchemy 2.0 and AsyncSession.
Transactions are kept open using session.flush() instead of commit(), ensuring the
caller (e.g. Service or Unit of Work) retains full control over transaction boundaries.
"""

from typing import Generic, TypeVar
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.application.common.repository import IRepository

# ModelType represents the SQLAlchemy ORM model class being persisted
ModelType = TypeVar("ModelType")


class BaseRepository(IRepository[ModelType], Generic[ModelType]):
    """Generic SQLAlchemy 2.0 concrete implementation of the IRepository interface.

    This class provides robust, reusable asynchronous CRUD methods for any ORM model
    inheriting from DeclarativeBase and TimestampMixin.
    """

    def __init__(self, session: AsyncSession, model_class: type[ModelType]) -> None:
        """Initialize the repository with an active database session and target model class.

        Args:
            session: SQLAlchemy AsyncSession used to execute asynchronous queries.
            model_class: The ORM model class managed by this repository instance.
        """
        # _session = active async connection to the database
        self._session = session
        # _model_class = the SQLAlchemy declarative class (e.g. UserModel, CategoryModel)
        self._model_class = model_class

    async def get_by_id(self, id: str) -> ModelType | None:
        """Retrieve a single entity by its primary key id.

        Args:
            id: Unique identifier string of the entity.

        Returns:
            The model instance if found, or None if no record matches.
        """
        # Modern SQLAlchemy 2.0 select syntax: select(Model).where(Model.id == id)
        stmt = select(self._model_class).where(self._model_class.id == id)
        result = await self._session.execute(stmt)
        # scalar_one_or_none returns exactly one model or None (raises if multiple records match)
        return result.scalar_one_or_none()

    async def list_all(self, limit: int = 20, offset: int = 0) -> list[ModelType]:
        """Retrieve a paginated collection of entities.

        Args:
            limit: Maximum number of records to return (default: 20).
            offset: Number of records to skip before returning results (default: 0).

        Returns:
            A list containing the matched model instances.
        """
        # Build query with pagination offset and limit
        stmt = select(self._model_class).offset(offset).limit(limit)
        result = await self._session.execute(stmt)
        # scalars().all() extracts the model instances from the Result object into a sequence
        return list(result.scalars().all())

    async def add(self, entity: ModelType) -> ModelType:
        """Add a new entity instance to the database session and flush.

        Args:
            entity: The new model instance to persist.

        Returns:
            The persisted model instance with database-generated attributes refreshed.
        """
        # Add to the session's pending insertion set
        self._session.add(entity)
        # flush() sends the SQL INSERT to the database without finalizing/committing transaction
        await self._session.flush()
        # refresh() re-reads server-generated attributes (like ID, created_at, updated_at)
        await self._session.refresh(entity)
        return entity

    async def update(self, entity: ModelType) -> ModelType:
        """Merge modifications made to an entity into the session and flush.

        Args:
            entity: The modified model instance.

        Returns:
            The merged persistent model instance.
        """
        # merge() synchronizes in-memory object state with the database identity map
        merged_entity = await self._session.merge(entity)
        # flush() sends the SQL UPDATE statement to the database
        await self._session.flush()
        return merged_entity

    async def delete(self, id: str) -> None:
        """Delete an entity by its primary key identifier if found, then flush.

        Args:
            id: Unique primary key identifier string of the entity to delete.
        """
        # Retrieve the entity first so SQLAlchemy tracks it in the identity map
        entity = await self.get_by_id(id)
        if entity is not None:
            # Mark entity for deletion in the current transaction
            await self._session.delete(entity)
            # flush() executes the SQL DELETE statement immediately
            await self._session.flush()
