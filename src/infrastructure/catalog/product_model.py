"""Product ORM model for catalog infrastructure layer.

This module defines the database representation of catalog products using
SQLAlchemy 2.0 declarative mapping, inheriting from TimestampMixin and Base.
"""

from typing import TYPE_CHECKING
from sqlalchemy import Boolean, ForeignKey, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from src.core.database import Base
from src.infrastructure.database.base_model import TimestampMixin

if TYPE_CHECKING:
    from src.infrastructure.catalog.category_model import CategoryModel


class ProductModel(TimestampMixin, Base):
    """SQLAlchemy ORM model representing the 'products' table.

    A product is a top-level catalog entry representing a sellable commodity.
    It contains textual details, SEO routing slugs, and links to an optional
    category taxonomy node.

    Attributes:
        id: 32-character hex UUID primary key (inherited from TimestampMixin).
        name: Human-readable product title.
        slug: Unique URL-safe slug for SEO and routing.
        category_id: Nullable foreign key pointing to categories.id.
        description: Long-form text or Markdown description.
        is_published: Visibility toggle allowing draft products before launch.
        category: Relationship loading the associated CategoryModel.
        created_at: Automatic UTC creation timestamp (from TimestampMixin).
        updated_at: Automatic UTC update timestamp (from TimestampMixin).
    """

    __tablename__ = "products"

    # Human-readable product title displayed on storefront and invoice
    name: Mapped[str] = mapped_column(
        String(255),
        nullable=False,
    )

    # Unique URL-friendly slug used in product page routing (e.g. /products/cotton-t-shirt)
    slug: Mapped[str] = mapped_column(
        String(255),
        unique=True,
        index=True,
        nullable=False,
    )

    # Foreign key referencing the categories table; SET NULL allows category deletion without losing products
    category_id: Mapped[str | None] = mapped_column(
        String(32),
        ForeignKey("categories.id", ondelete="SET NULL"),
        nullable=True,
        default=None,
        index=True,
    )

    # Optional detailed text or markdown description of the item
    description: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
        default=None,
    )

    # Publication toggle: False keeps the product hidden as an internal draft
    is_published: Mapped[bool] = mapped_column(
        Boolean,
        default=False,
        nullable=False,
        index=True,
    )

    # Many-to-One relationship back to the parent CategoryModel
    category: Mapped["CategoryModel | None"] = relationship(
        "src.infrastructure.catalog.category_model.CategoryModel",
        lazy="select",
    )
