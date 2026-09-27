"""Category API endpoints and request/response schemas for API v1.

This module provides HTTP CRUD routes for product categories, allowing clients
to create root and child categories, retrieve paginated flat lists, and inspect
category details by unique URL slug.
"""

import re
import unicodedata
import uuid
from fastapi import APIRouter, Depends, Query, status
from pydantic import Field
from sqlalchemy.ext.asyncio import AsyncSession

from src.api.common.schemas import ApiResponse, BaseResponseSchema, BaseSchema
from src.core.database import get_db
from src.domain.common.exceptions import (
    DuplicateEntityException,
    EntityNotFoundException,
)
from src.infrastructure.catalog.category_model import CategoryModel
from src.infrastructure.catalog.category_repository import CategoryRepository

router = APIRouter(prefix="/categories", tags=["Categories"])


def _generate_slug(name: str) -> str:
    """Generate a clean, URL-friendly slug from a text string.

    Converts accented characters to plain ASCII, handles Vietnamese letters
    like 'đ'/'Đ', and substitutes whitespace and punctuation with single hyphens.

    Args:
        name: Human-readable name (e.g. 'Thời trang', 'Men's Shoes').

    Returns:
        A lowercase URL-safe slug string (e.g. 'thoi-trang', 'mens-shoes').
    """
    text = name.replace("đ", "d").replace("Đ", "D")
    text = unicodedata.normalize("NFKD", text).encode("ascii", "ignore").decode("ascii")
    text = re.sub(r"[^\w\s-]", "", text).strip().lower()
    slug = re.sub(r"[-\s]+", "-", text)
    return slug or uuid.uuid4().hex[:8]


# --- Request & Response DTO Schemas ---


class CategoryCreateRequest(BaseSchema):
    """Payload schema for creating a new product category.

    Attributes:
        name: Category display title (required, 1-255 characters).
        slug: Optional custom URL slug; automatically generated if omitted.
        parent_id: Optional 32-character UUID string of the parent category.
        is_active: Whether the category is active and visible to customers.
    """

    name: str = Field(
        ...,
        min_length=1,
        max_length=255,
        description="Display name of the category",
    )
    slug: str | None = Field(
        default=None,
        max_length=255,
        description="Unique URL slug (auto-generated from name if omitted)",
    )
    parent_id: str | None = Field(
        default=None,
        description="Unique ID of the parent category, or null for root category",
    )
    is_active: bool = Field(
        default=True,
        description="Whether this category is published and visible",
    )


class CategoryResponse(BaseResponseSchema):
    """Response schema representing a category entity.

    Attributes:
        id: 32-character hex UUID identifier.
        name: Category title.
        slug: Unique URL-safe identifier.
        parent_id: Parent category ID, or None if root.
        is_active: Visibility status.
        created_at: UTC timestamp when the record was created.
        updated_at: UTC timestamp when the record was last modified.
    """

    name: str
    slug: str
    parent_id: str | None
    is_active: bool


# --- API Endpoints ---


@router.post(
    "",
    response_model=ApiResponse[CategoryResponse],
    status_code=status.HTTP_201_CREATED,
    summary="Create a new category",
    description="Create a root category or a subcategory by providing an optional parent_id.",
)
async def create_category(
    request: CategoryCreateRequest,
    db: AsyncSession = Depends(get_db),
) -> ApiResponse[CategoryResponse]:
    """Create a new category record.

    Validates that:
    1. The slug is unique across all categories.
    2. If parent_id is supplied, the referenced parent category exists.
    """
    repo = CategoryRepository(db)

    # 1. Determine final slug: use custom slug if provided, else auto-slugify name
    raw_slug = request.slug.strip() if request.slug else _generate_slug(request.name)

    # 2. Check for duplicate slug uniqueness conflict
    existing_by_slug = await repo.get_by_slug(raw_slug)
    if existing_by_slug is not None:
        raise DuplicateEntityException(f"Category with slug '{raw_slug}' already exists")

    # 3. Validate parent existence if parent_id is specified
    if request.parent_id is not None:
        parent = await repo.get_by_id(request.parent_id)
        if parent is None:
            raise EntityNotFoundException("Category", request.parent_id)

    # 4. Instantiate ORM entity and persist via repository
    category = CategoryModel(
        name=request.name.strip(),
        slug=raw_slug,
        parent_id=request.parent_id,
        is_active=request.is_active,
    )
    created_category = await repo.add(category)

    # 5. Commit transaction boundary at API layer
    await db.commit()

    return ApiResponse(
        data=CategoryResponse.model_validate(created_category),
        message="Category created successfully",
    )


@router.get(
    "",
    response_model=ApiResponse[list[CategoryResponse]],
    status_code=status.HTTP_200_OK,
    summary="List all categories",
    description="Retrieve a paginated flat list of all categories in the system.",
)
async def list_categories(
    limit: int = Query(default=20, ge=1, le=100, description="Maximum number of items to return"),
    offset: int = Query(default=0, ge=0, description="Number of items to skip"),
    db: AsyncSession = Depends(get_db),
) -> ApiResponse[list[CategoryResponse]]:
    """Retrieve a flat collection of categories with limit/offset pagination."""
    repo = CategoryRepository(db)
    categories = await repo.list_all(limit=limit, offset=offset)

    return ApiResponse(
        data=[CategoryResponse.model_validate(c) for c in categories],
        message="Categories retrieved successfully",
    )


@router.get(
    "/{slug}",
    response_model=ApiResponse[CategoryResponse],
    status_code=status.HTTP_200_OK,
    summary="Get category details by slug",
    description="Retrieve full details of a specific category using its unique slug or ID.",
)
async def get_category(
    slug: str,
    db: AsyncSession = Depends(get_db),
) -> ApiResponse[CategoryResponse]:
    """Retrieve a single category by its slug (or fallback to ID if no slug matches)."""
    repo = CategoryRepository(db)

    # Lookup primarily by URL slug
    category = await repo.get_by_slug(slug)
    # Secondary fallback to ID lookup
    if category is None:
        category = await repo.get_by_id(slug)

    if category is None:
        raise EntityNotFoundException("Category", slug)

    return ApiResponse(
        data=CategoryResponse.model_validate(category),
        message="Category retrieved successfully",
    )
