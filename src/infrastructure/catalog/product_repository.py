"""Product repository implementation for catalog infrastructure layer.

This module provides data access operations for ProductModel entities,
extending the generic BaseRepository with product-specific query methods.
"""

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from src.infrastructure.catalog.product_model import ProductModel
from src.infrastructure.database.base_repository import BaseRepository


class ProductRepository(BaseRepository[ProductModel]):
    """Repository handling database operations for ProductModel entities.

    Inherits standard asynchronous CRUD operations (get_by_id, list_all, add,
    update, delete) from BaseRepository and provides specialized query methods
    such as slug lookup and total count estimation.
    """

    def __init__(self, session: AsyncSession) -> None:
        """Initialize the product repository with an active async database session.

        Args:
            session: SQLAlchemy AsyncSession used to execute asynchronous queries.
        """
        super().__init__(session, ProductModel)

    async def get_by_slug(self, slug: str) -> ProductModel | None:
        """Retrieve a product by its unique URL-friendly slug.

        Args:
            slug: URL-friendly identifier string (e.g. 'classic-cotton-t-shirt').

        Returns:
            The ProductModel instance if found, or None if no product matches.
        """
        stmt = select(ProductModel).where(ProductModel.slug == slug)
        result = await self._session.execute(stmt)
        return result.scalar_one_or_none()

    async def count(self) -> int:
        """Count the total number of products currently stored in the database.

        Useful for computing total records and has_next flags in paginated responses.

        Returns:
            Total product count as an integer.
        """
        stmt = select(func.count()).select_from(ProductModel)
        result = await self._session.execute(stmt)
        return result.scalar() or 0
