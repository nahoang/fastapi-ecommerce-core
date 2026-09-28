"""Product variant ORM model for catalog infrastructure layer.

This module defines the database representation of product variants using
SQLAlchemy 2.0 declarative mapping, inheriting from TimestampMixin and Base.
"""

from decimal import Decimal
from typing import TYPE_CHECKING
from sqlalchemy import ForeignKey, Numeric, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from src.core.database import Base
from src.infrastructure.database.base_model import TimestampMixin

if TYPE_CHECKING:
    from src.infrastructure.catalog.product_model import ProductModel


class ProductVariantModel(TimestampMixin, Base):
    """SQLAlchemy ORM model representing the 'product_variants' table.

    A product variant is a specific purchasable variation of a parent product,
    differentiated by attributes such as size, color, or configuration.
    Each variant holds an individual SKU, display name, and pricing.

    Attributes:
        id: 32-character hex UUID primary key (inherited from TimestampMixin).
        product_id: Foreign key referencing products.id (CASCADE on delete).
        sku: Unique Stock Keeping Unit identifier across all inventory items.
        name: Human-readable variant title (e.g. 'Size M / Red').
        price_amount: Unit price stored with exact Decimal/NUMERIC precision.
        currency: ISO 4217 3-letter currency code (e.g. 'USD').
        product: Relationship back to the parent ProductModel.
        created_at: Automatic UTC creation timestamp (from TimestampMixin).
        updated_at: Automatic UTC update timestamp (from TimestampMixin).
    """

    __tablename__ = "product_variants"

    # Foreign key referencing parent product; CASCADE removes variants when product is deleted
    product_id: Mapped[str] = mapped_column(
        String(32),
        ForeignKey("products.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    # Unique Stock Keeping Unit (e.g. 'TSHIRT-RED-M') used for inventory tracking
    sku: Mapped[str] = mapped_column(
        String(100),
        unique=True,
        index=True,
        nullable=False,
    )

    # Human-readable variant title (e.g. 'Size M / Navy Blue')
    name: Mapped[str] = mapped_column(
        String(255),
        nullable=False,
    )

    # Unit price strictly stored as Numeric(12, 2) to prevent binary floating-point roundoff errors
    price_amount: Mapped[Decimal] = mapped_column(
        Numeric(12, 2),
        nullable=False,
    )

    # Standard 3-letter ISO currency code (defaults to 'USD')
    currency: Mapped[str] = mapped_column(
        String(3),
        default="USD",
        nullable=False,
    )

    # Bidirectional Many-to-One relationship back to parent ProductModel
    product: Mapped["ProductModel"] = relationship(
        "src.infrastructure.catalog.product_model.ProductModel",
        back_populates="variants",
        lazy="select",
    )
