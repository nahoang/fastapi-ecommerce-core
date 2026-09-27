"""Category ORM model for catalog infrastructure layer.

This module defines the database representation of catalog categories using
SQLAlchemy 2.0 declarative mapping, inheriting from TimestampMixin and Base.
It supports hierarchical structures via a self-referential foreign key.
"""

from sqlalchemy import Boolean, ForeignKey, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from src.core.database import Base
from src.infrastructure.database.base_model import TimestampMixin


class CategoryModel(TimestampMixin, Base):
    """SQLAlchemy ORM model representing the 'categories' table.

    A category organizes products into a logical tree or flat hierarchy.
    Self-referential parent_id enables subcategories (e.g. Clothing -> Shirts).

    Attributes:
        id: 32-character hex UUID primary key (inherited from TimestampMixin).
        name: Human-readable category title.
        slug: Unique URL-safe slug for search engine indexing and routing.
        parent_id: Nullable foreign key pointing to the parent category's ID.
        is_active: Flag indicating whether this category is active and visible.
        parent: Self-referential relationship loading the parent CategoryModel.
        created_at: Automatic UTC creation timestamp (from TimestampMixin).
        updated_at: Automatic UTC update timestamp (from TimestampMixin).
    """

    __tablename__ = "categories"

    # Category name displayed to customers and administrators
    name: Mapped[str] = mapped_column(
        String(255),
        nullable=False,
    )

    # Unique URL-friendly identifier used in route parameters (e.g. /categories/t-shirts)
    slug: Mapped[str] = mapped_column(
        String(255),
        unique=True,
        index=True,
        nullable=False,
    )

    # Self-referential foreign key pointing to categories.id; null indicates a top-level root category
    parent_id: Mapped[str | None] = mapped_column(
        String(32),
        ForeignKey("categories.id", ondelete="SET NULL"),
        nullable=True,
        default=None,
    )

    # Active status toggle allowing administrators to hide entire category trees
    is_active: Mapped[bool] = mapped_column(
        Boolean,
        default=True,
        nullable=False,
    )

    # Self-referential relationship to the parent category
    # remote_side specifies which column represents the "one" side in this 1-N hierarchy
    parent: Mapped["CategoryModel | None"] = relationship(
        "CategoryModel",
        remote_side=lambda: [CategoryModel.id],
    )
