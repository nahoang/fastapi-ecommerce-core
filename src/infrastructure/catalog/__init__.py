"""Catalog infrastructure package."""

from src.infrastructure.catalog.category_model import CategoryModel
from src.infrastructure.catalog.category_repository import CategoryRepository

__all__ = [
    "CategoryModel",
    "CategoryRepository",
]
