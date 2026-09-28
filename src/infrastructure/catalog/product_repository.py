"""Product repository implementation for catalog infrastructure layer.

This module provides data access operations for ProductModel entities,
extending the generic BaseRepository with product-specific query methods.
"""

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

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
        """Retrieve a product by its unique URL-friendly slug, eagerly loading variants.

        Uses selectinload to eagerly fetch associated variants in a single batch query,
        strictly preventing N+1 queries and avoiding MissingGreenlet errors in async contexts.

        Args:
            slug: URL-friendly identifier string (e.g. 'classic-cotton-t-shirt').

        Returns:
            The ProductModel instance with variants populated, or None if no product matches.
        """
        stmt = (
            select(ProductModel)
            .options(selectinload(ProductModel.variants))
            .where(ProductModel.slug == slug)
        )
        result = await self._session.execute(stmt)
        return result.scalar_one_or_none()

    async def get_by_id(self, id: str) -> ProductModel | None:
        """Retrieve a single product by primary key id, eagerly loading variants.

        Args:
            id: Unique identifier string of the product.

        Returns:
            The ProductModel instance with variants populated, or None if not found.
        """
        stmt = (
            select(ProductModel)
            .options(selectinload(ProductModel.variants))
            .where(ProductModel.id == id)
        )
        result = await self._session.execute(stmt)
        return result.scalar_one_or_none()

    async def list_all(self, limit: int = 20, offset: int = 0) -> list[ProductModel]:
        """Retrieve a paginated collection of products, eagerly loading variants.

        Args:
            limit: Maximum number of records to return (default: 20).
            offset: Number of records to skip before returning results (default: 0).

        Returns:
            List of ProductModel instances with variants populated.
        """
        stmt = (
            select(ProductModel)
            .options(selectinload(ProductModel.variants))
            .order_by(ProductModel.created_at.desc())
            .limit(limit)
            .offset(offset)
        )
        result = await self._session.execute(stmt)
        return list(result.scalars().all())

    async def count(self) -> int:
        """Count the total number of products currently stored in the database.

        Useful for computing total records and has_next flags in paginated responses.

        Returns:
            Total product count as an integer.
        """
        stmt = select(func.count()).select_from(ProductModel)
        result = await self._session.execute(stmt)
        return result.scalar() or 0

