"""Product variant repository implementation for catalog infrastructure layer.

This module provides data access operations for ProductVariantModel entities,
extending the generic BaseRepository with SKU lookup and variant-specific methods.
"""

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.infrastructure.catalog.product_variant_model import ProductVariantModel
from src.infrastructure.database.base_repository import BaseRepository


class ProductVariantRepository(BaseRepository[ProductVariantModel]):
    """Repository handling database operations for ProductVariantModel entities.

    Provides operations for creating, retrieving, and validating product variants,
    including unique SKU checks and filtering by parent product.
    """

    def __init__(self, session: AsyncSession) -> None:
        """Initialize the product variant repository with an active async database session.

        Args:
            session: SQLAlchemy AsyncSession used to execute asynchronous queries.
        """
        super().__init__(session, ProductVariantModel)

    async def get_by_sku(self, sku: str) -> ProductVariantModel | None:
        """Retrieve a product variant by its unique SKU.

        Args:
            sku: Stock Keeping Unit identifier (e.g. 'TSHIRT-RED-M').

        Returns:
            The ProductVariantModel instance if found, or None if no match.
        """
        stmt = select(ProductVariantModel).where(ProductVariantModel.sku == sku)
        result = await self._session.execute(stmt)
        return result.scalar_one_or_none()

    async def list_by_product_id(self, product_id: str) -> list[ProductVariantModel]:
        """Retrieve all variants belonging to a specific product.

        Args:
            product_id: 32-character hex UUID of the parent product.

        Returns:
            List of ProductVariantModel instances.
        """
        stmt = (
            select(ProductVariantModel)
            .where(ProductVariantModel.product_id == product_id)
            .order_by(ProductVariantModel.created_at.asc())
        )
        result = await self._session.execute(stmt)
        return list(result.scalars().all())
