"""Product API endpoints and request/response schemas for API v1.

This module provides HTTP CRUD routes for catalog products, allowing clients
to create products, retrieve paginated product listings, and inspect
product details by unique URL slug.
"""

import re
import unicodedata
import uuid
from fastapi import APIRouter, Depends, Query, status
from pydantic import Field
from sqlalchemy.ext.asyncio import AsyncSession

from src.api.common.schemas import ApiResponse, BaseResponseSchema, BaseSchema, PaginatedResponse
from src.core.database import get_db
from src.domain.common.exceptions import DuplicateEntityException, EntityNotFoundException
from src.infrastructure.catalog.category_repository import CategoryRepository
from src.infrastructure.catalog.product_model import ProductModel
from src.infrastructure.catalog.product_repository import ProductRepository

router = APIRouter(prefix="/products", tags=["Products"])


def _generate_slug(name: str) -> str:
    """Generate a clean, URL-friendly slug from a text string.

    Converts accented characters to plain ASCII, handles Vietnamese letters
    like 'đ'/'Đ', and substitutes whitespace and punctuation with single hyphens.

    Args:
        name: Human-readable title (e.g. 'Áo thun cotton', 'Mechanical Keyboard').

    Returns:
        A lowercase URL-safe slug string (e.g. 'ao-thun-cotton', 'mechanical-keyboard').
    """
    text = name.replace("đ", "d").replace("Đ", "D")
    text = unicodedata.normalize("NFKD", text).encode("ascii", "ignore").decode("ascii")
    text = re.sub(r"[^\w\s-]", "", text).strip().lower()
    slug = re.sub(r"[-\s]+", "-", text)
    return slug or uuid.uuid4().hex[:8]


# --- Request & Response DTO Schemas ---


class ProductCreateRequest(BaseSchema):
    """Payload schema for creating a new catalog product.

    Attributes:
        name: Product title (required, 1-255 characters).
        slug: Optional custom URL slug; automatically generated if omitted.
        category_id: Optional 32-character UUID string of the parent category.
        description: Optional detailed textual description of the product.
        is_published: Whether the product is immediately visible to customers.
    """

    name: str = Field(
        ...,
        min_length=1,
        max_length=255,
        description="Display title of the product",
    )
    slug: str | None = Field(
        default=None,
        max_length=255,
        description="Unique URL slug (auto-generated from name if omitted)",
    )
    category_id: str | None = Field(
        default=None,
        description="Unique ID of the parent category, or null if unassigned",
    )
    description: str | None = Field(
        default=None,
        description="Markdown or plain text description of the product",
    )
    is_published: bool = Field(
        default=False,
        description="Whether this product is live and visible to customers",
    )


class ProductResponse(BaseResponseSchema):
    """Response schema representing a product entity.

    Attributes:
        id: 32-character hex UUID identifier.
        name: Product title.
        slug: Unique URL-safe identifier.
        category_id: Associated category ID, or None if unassigned.
        description: Detailed product description.
        is_published: Visibility toggle status.
        created_at: UTC timestamp when the record was created.
        updated_at: UTC timestamp when the record was last modified.
    """

    name: str
    slug: str
    category_id: str | None = None
    description: str | None = None
    is_published: bool = False


# --- API Endpoints ---


@router.post(
    "",
    response_model=ApiResponse[ProductResponse],
    status_code=status.HTTP_201_CREATED,
    summary="Create a new product",
    description="Create a product with optional category linkage, SEO slug, and description.",
)
async def create_product(
    request: ProductCreateRequest,
    db: AsyncSession = Depends(get_db),
) -> ApiResponse[ProductResponse]:
    """Create a new product record.

    Validates that:
    1. The slug is unique across all products.
    2. If category_id is supplied, the referenced category exists.
    """
    repo = ProductRepository(db)

    # 1. Determine final slug: use custom slug if provided, else auto-slugify name
    raw_slug = request.slug.strip() if request.slug else _generate_slug(request.name)

    # 2. Check for duplicate slug uniqueness conflict
    existing_by_slug = await repo.get_by_slug(raw_slug)
    if existing_by_slug is not None:
        raise DuplicateEntityException(f"Product with slug '{raw_slug}' already exists")

    # 3. Validate category existence if category_id is specified
    if request.category_id is not None:
        category_repo = CategoryRepository(db)
        category = await category_repo.get_by_id(request.category_id)
        if category is None:
            raise EntityNotFoundException("Category", request.category_id)

    # 4. Instantiate ORM entity and persist via repository
    product = ProductModel(
        name=request.name.strip(),
        slug=raw_slug,
        category_id=request.category_id,
        description=request.description.strip() if request.description else None,
        is_published=request.is_published,
    )
    created_product = await repo.add(product)

    # 5. Commit transaction boundary at API layer
    await db.commit()

    return ApiResponse(
        data=ProductResponse.model_validate(created_product),
        message="Product created successfully",
    )


@router.get(
    "",
    response_model=PaginatedResponse[ProductResponse],
    status_code=status.HTTP_200_OK,
    summary="List products",
    description="Retrieve a paginated list of catalog products.",
)
async def list_products(
    limit: int = Query(default=20, ge=1, le=100, description="Maximum number of items to return"),
    offset: int = Query(default=0, ge=0, description="Number of items to skip"),
    db: AsyncSession = Depends(get_db),
) -> PaginatedResponse[ProductResponse]:
    """Retrieve a paginated collection of products with limit/offset."""
    repo = ProductRepository(db)

    # 1. Fetch total count of products in database
    total = await repo.count()

    # 2. Fetch slice of products using limit and offset
    products = await repo.list_all(limit=limit, offset=offset)

    # 3. Compute 1-indexed page number from offset and limit
    page = (offset // limit) + 1 if limit > 0 else 1

    # 4. Return standardized PaginatedResponse envelope
    return PaginatedResponse.create(
        data=[ProductResponse.model_validate(p) for p in products],
        total=total,
        page=page,
        page_size=limit,
    )


@router.get(
    "/{slug}",
    response_model=ApiResponse[ProductResponse],
    status_code=status.HTTP_200_OK,
    summary="Get product details by slug",
    description="Retrieve full details of a specific product using its unique slug or ID.",
)
async def get_product(
    slug: str,
    db: AsyncSession = Depends(get_db),
) -> ApiResponse[ProductResponse]:
    """Retrieve a single product by its slug (or fallback to ID if no slug matches)."""
    repo = ProductRepository(db)

    # 1. Lookup primarily by URL slug
    product = await repo.get_by_slug(slug)

    # 2. Secondary fallback to ID lookup
    if product is None:
        product = await repo.get_by_id(slug)

    # 3. Raise 404 if product still not found
    if product is None:
        raise EntityNotFoundException("Product", slug)

    return ApiResponse(
        data=ProductResponse.model_validate(product),
        message="Product retrieved successfully",
    )
