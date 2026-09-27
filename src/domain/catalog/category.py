"""Category domain entity — pure Python, zero framework dependencies.

In Clean Architecture, domain entities represent business models and rules.
They remain completely independent of persistence mechanisms, web frameworks,
and external libraries.
"""

from dataclasses import dataclass
from src.domain.common.entities import BaseEntity


@dataclass(kw_only=True)
class Category(BaseEntity):
    """Product category entity within the catalog domain.

    Categories can form hierarchical structures through self-referential
    parent-child relationships (e.g. Clothing -> Men's Clothing -> T-Shirts).

    Attributes:
        name: Human-readable name of the category (e.g. 'Clothing').
        slug: Unique URL-friendly identifier string (e.g. 'clothing').
        parent_id: Optional ID of the parent category, or None if root.
        is_active: Boolean flag indicating whether the category is visible/active.
    """

    name: str
    slug: str
    parent_id: str | None = None
    is_active: bool = True
