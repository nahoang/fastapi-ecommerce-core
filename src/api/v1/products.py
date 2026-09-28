"""Product API endpoints and request/response schemas for API v1.

This module provides HTTP CRUD routes for catalog products and product variants,
allowing clients to create products with variants, add variants to existing products,
retrieve paginated product listings, and inspect product details with variants by slug.
"""

from decimal import Decimal
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
from src.infrastructure.catalog.product_variant_model import ProductVariantModel
from src.infrastructure.catalog.product_variant_repository import ProductVariantRepository

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


class ProductVariantCreateRequest(BaseSchema):
    """Payload schema for creating a new product variant.

    Attributes:
        sku: Stock Keeping Unit (required, 1-100 characters).
        name: Variant title (required, 1-255 characters, e.g. 'Size M / Red').
        price_amount: Price as Decimal (required, strictly Decimal, ge=0).
        currency: ISO 4217 3-letter currency code (default: 'USD').
    """

    sku: str = Field(
        ...,
        min_length=1,
        max_length=100,
        description="Unique Stock Keeping Unit identifier (e.g. 'TSHIRT-RED-M')",
    )
    name: str = Field(
        ...,
        min_length=1,
        max_length=255,
        description="Display title of the variant (e.g. 'Size M / Red')",
    )
    price_amount: Decimal = Field(
        ...,
        ge=Decimal("0.00"),
        description="Unit price strictly stored as Decimal to prevent precision loss",
    )
    currency: str = Field(
        default="USD",
        min_length=3,
        max_length=3,
        description="ISO 4217 3-letter currency code (e.g. 'USD', 'VND')",
    )


class ProductVariantResponse(BaseResponseSchema):
    """Response schema representing a product variant entity.

    Attributes:
        id: 32-character hex UUID identifier.
        product_id: 32-character hex UUID of the parent product.
        sku: Unique Stock Keeping Unit.
        name: Human-readable variant title.
        price_amount: Unit price as Decimal.
        currency: ISO 4217 currency code.
        created_at: UTC timestamp when the record was created.
        updated_at: UTC timestamp when the record was last modified.
    """

    product_id: str
    sku: str
    name: str
    price_amount: Decimal
    currency: str


class ProductCreateRequest(BaseSchema):
    """Payload schema for creating a new catalog product.

    Attributes:
        name: Product title (required, 1-255 characters).
        slug: Optional custom URL slug; automatically generated if omitted.
        category_id: Optional 32-character UUID string of the parent category.
        description: Optional detailed textual description of the product.
        is_published: Whether the product is immediately visible to customers.
        variants: Optional initial variants to create along with the product.
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
    variants: list[ProductVariantCreateRequest] = Field(
        default_factory=list,
        description="Optional list of initial variants to attach to this product",
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
        variants: List of associated product variants.
        created_at: UTC timestamp when the record was created.
        updated_at: UTC timestamp when the record was last modified.
    """

    name: str
    slug: str
    category_id: str | None = None
    description: str | None = None
    is_published: bool = False
    variants: list[ProductVariantResponse] = Field(default_factory=list)


# --- API Endpoints ---


@router.post(
    "",
    response_model=ApiResponse[ProductResponse],
    status_code=status.HTTP_201_CREATED,
    summary="Create a new product",
    description="Create a product with optional category linkage, SEO slug, description, and initial variants.",
)
async def create_product(
    request: ProductCreateRequest,
    db: AsyncSession = Depends(get_db),
) -> ApiResponse[ProductResponse]:
    """Create a new product record.

    Validates that:
    1. The slug is unique across all products.
    2. If category_id is supplied, the referenced category exists.
    3. If initial variants are supplied, their SKUs are unique.
    """
    repo = ProductRepository(db)
    variant_repo = ProductVariantRepository(db)

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

    # 4. Check SKU uniqueness for any initial variants
    if request.variants:
        skus_in_payload = [v.sku.strip() for v in request.variants]
        if len(skus_in_payload) != len(set(skus_payload := skus_in_payload)):
            raise DuplicateEntityException("Duplicate SKU found in variants payload")
        for sku in skus_payload:
            existing_variant = await variant_repo.get_by_sku(sku)
            if existing_variant is not None:
                raise DuplicateEntityException(f"Variant with SKU '{sku}' already exists")

    # 5. Instantiate ORM entity and persist via repository
    product = ProductModel(
        name=request.name.strip(),
        slug=raw_slug,
        category_id=request.category_id,
        description=request.description.strip() if request.description else None,
        is_published=request.is_published,
    )

    if request.variants:
        for v in request.variants:
            product.variants.append(
                ProductVariantModel(
                    sku=v.sku.strip(),
                    name=v.name.strip(),
                    price_amount=v.price_amount,
                    currency=v.currency.upper(),
                )
            )

    created_product = await repo.add(product)

    # 6. Commit transaction boundary at API layer
    await db.commit()

    # Re-fetch with selectinload to guarantee relationships are fully populated
    refetched = await repo.get_by_id(created_product.id)
    return ApiResponse(
        data=ProductResponse.model_validate(refetched or created_product),
        message="Product created successfully",
    )


@router.post(
    "/{product_id}/variants",
    response_model=ApiResponse[ProductVariantResponse],
    status_code=status.HTTP_201_CREATED,
    summary="Create a product variant",
    description="Add a new SKU variant to an existing product.",
)
async def create_product_variant(
    product_id: str,
    request: ProductVariantCreateRequest,
    db: AsyncSession = Depends(get_db),
) -> ApiResponse[ProductVariantResponse]:
    """Create a new variant under an existing product.

    Validates that:
    1. The parent product exists.
    2. The SKU is globally unique across all variants.
    """
    product_repo = ProductRepository(db)
    variant_repo = ProductVariantRepository(db)

    # 1. Validate parent product existence
    product = await product_repo.get_by_id(product_id)
    if product is None:
        raise EntityNotFoundException("Product", product_id)

    # 2. Check for duplicate SKU
    clean_sku = request.sku.strip()
    existing_variant = await variant_repo.get_by_sku(clean_sku)
    if existing_variant is not None:
        raise DuplicateEntityException(f"Variant with SKU '{clean_sku}' already exists")

    # 3. Create and persist variant
    variant = ProductVariantModel(
        product_id=product.id,
        sku=clean_sku,
        name=request.name.strip(),
        price_amount=request.price_amount,
        currency=request.currency.upper(),
    )
    created_variant = await variant_repo.add(variant)
    await db.commit()

    return ApiResponse(
        data=ProductVariantResponse.model_validate(created_variant),
        message="Product variant created successfully",
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

    # 2. Fetch slice of products using limit and offset (uses selectinload on variants)
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
    description="Retrieve full details of a specific product with its variants using its unique slug or ID.",
)
async def get_product(
    slug: str,
    db: AsyncSession = Depends(get_db),
) -> ApiResponse[ProductResponse]:
    """Retrieve a single product by its slug (or fallback to ID if no slug matches)."""
    repo = ProductRepository(db)

    # 1. Lookup primarily by URL slug (uses selectinload on variants)
    product = await repo.get_by_slug(slug)

    # 2. Secondary fallback to ID lookup (uses selectinload on variants)
    if product is None:
        product = await repo.get_by_id(slug)

    # 3. Raise 404 if product still not found
    if product is None:
        raise EntityNotFoundException("Product", slug)

    return ApiResponse(
        data=ProductResponse.model_validate(product),
        message="Product retrieved successfully",
    )
