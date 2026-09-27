"""Category repository implementation for catalog infrastructure layer.

This module provides data access operations for CategoryModel entities,
extending the generic BaseRepository with category-specific query methods.
"""

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.infrastructure.catalog.category_model import CategoryModel
from src.infrastructure.database.base_repository import BaseRepository


class CategoryRepository(BaseRepository[CategoryModel]):
    """Repository handling database operations for CategoryModel entities.

    Inherits standard asynchronous CRUD operations (get_by_id, list_all, add,
    update, delete) from BaseRepository and provides slug-based retrieval.
    """

    def __init__(self, session: AsyncSession) -> None:
        """Initialize the category repository with an active async database session.

        Args:
            session: SQLAlchemy AsyncSession for executing asynchronous queries.
        """
        super().__init__(session, CategoryModel)

    async def get_by_slug(self, slug: str) -> CategoryModel | None:
        """Retrieve a category by its unique URL-friendly slug.

        Args:
            slug: URL-friendly identifier string (e.g. 'clothing', 'men').

        Returns:
            The CategoryModel instance if found, or None if no category matches.
        """
        # Modern SQLAlchemy 2.0 select query: select(CategoryModel).where(...)
        stmt = select(CategoryModel).where(CategoryModel.slug == slug)
        result = await self._session.execute(stmt)
        # scalar_one_or_none returns a single model instance or None if not found
        return result.scalar_one_or_none()
