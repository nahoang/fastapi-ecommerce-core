"""Product domain entity — pure Python, zero framework dependencies.

In Clean Architecture, domain entities represent core business concepts and rules.
They remain completely independent of persistence mechanisms (SQLAlchemy),
web frameworks (FastAPI), and serialization libraries.
"""

from dataclasses import dataclass
from src.domain.common.entities import BaseEntity


@dataclass(kw_only=True)
class Product(BaseEntity):
    """Product domain entity within the catalog domain.

    Represents a sellable catalog item managed by store administrators.
    Each product belongs to an optional category and holds essential
    metadata such as name, SEO slug, description, and publication state.

    Attributes:
        name: Human-readable title of the product (e.g. 'Classic Cotton T-Shirt').
        slug: Unique URL-friendly identifier string (e.g. 'classic-cotton-t-shirt').
        category_id: Optional UUID string pointing to the parent category.
        description: Optional long-form text or Markdown description of the product.
        is_published: Boolean flag indicating whether the product is visible to shoppers.
    """

    name: str
    slug: str
    category_id: str | None = None
    description: str | None = None
    is_published: bool = False
