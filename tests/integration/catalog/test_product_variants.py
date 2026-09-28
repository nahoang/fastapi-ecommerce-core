"""Integration tests for Product Variants and eager loading (selectinload).

Tests the full lifecycle of product variants through the HTTP interface and repository layer:
- Creating a product with 3 variants (Size M, L, XL) and fetching detail via slug.
- Verifying exact Decimal representation for monetary pricing.
- Creating products with inline initial variants.
- Enforcing global SKU uniqueness via API (409 Conflict) and database constraint (IntegrityError).
- Handling 404 Not Found when creating variants for nonexistent products.
- Validating selectinload eager loading behavior preventing N+1 queries in async mode.
"""

from decimal import Decimal
import pytest
from httpx import AsyncClient
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from src.infrastructure.catalog.product_model import ProductModel
from src.infrastructure.catalog.product_repository import ProductRepository
from src.infrastructure.catalog.product_variant_model import ProductVariantModel


@pytest.mark.asyncio
async def test_create_product_with_variants_and_read_detail(client: AsyncClient) -> None:
    """Test creating a product, adding 3 variants (Size M/L/XL), and fetching detail with variants."""
    # 1. Create a parent product
    product_payload = {
        "name": "Áo thun basic",
        "slug": "ao-thun-basic",
        "description": "Premium 100% combed cotton basic t-shirt.",
        "is_published": True,
    }
    prod_res = await client.post("/api/v1/products", json=product_payload)
    assert prod_res.status_code == 201
    prod_data = prod_res.json()["data"]
    product_id = prod_data["id"]

    # 2. Add 3 distinct variants (Size M, Size L, Size XL)
    variants_to_create = [
        {"sku": "TSHIRT-BASIC-M", "name": "Size M", "price_amount": "19.99", "currency": "USD"},
        {"sku": "TSHIRT-BASIC-L", "name": "Size L", "price_amount": "21.50", "currency": "USD"},
        {"sku": "TSHIRT-BASIC-XL", "name": "Size XL", "price_amount": "24.00", "currency": "USD"},
    ]
    for variant in variants_to_create:
        var_res = await client.post(f"/api/v1/products/{product_id}/variants", json=variant)
        assert var_res.status_code == 201
        var_data = var_res.json()["data"]
        assert var_data["sku"] == variant["sku"]
        assert var_data["name"] == variant["name"]
        assert Decimal(str(var_data["price_amount"])) == Decimal(variant["price_amount"])
        assert var_data["currency"] == variant["currency"]
        assert var_data["product_id"] == product_id

    # 3. Retrieve product details by slug: GET /api/v1/products/{slug}
    detail_res = await client.get("/api/v1/products/ao-thun-basic")
    assert detail_res.status_code == 200
    detail_json = detail_res.json()
    assert detail_json["message"] == "Product retrieved successfully"
    detail_data = detail_json["data"]

    # 4. Verify that response includes all 3 variants with exact Decimal pricing
    assert detail_data["id"] == product_id
    assert detail_data["name"] == "Áo thun basic"
    assert detail_data["slug"] == "ao-thun-basic"
    assert len(detail_data["variants"]) == 3

    skus = [v["sku"] for v in detail_data["variants"]]
    assert "TSHIRT-BASIC-M" in skus
    assert "TSHIRT-BASIC-L" in skus
    assert "TSHIRT-BASIC-XL" in skus

    # Verify Decimal financial precision for each returned variant
    variant_prices = {v["sku"]: Decimal(str(v["price_amount"])) for v in detail_data["variants"]}
    assert variant_prices["TSHIRT-BASIC-M"] == Decimal("19.99")
    assert variant_prices["TSHIRT-BASIC-L"] == Decimal("21.50")
    assert variant_prices["TSHIRT-BASIC-XL"] == Decimal("24.00")

    # 5. Also verify secondary lookup by product ID
    id_res = await client.get(f"/api/v1/products/{product_id}")
    assert id_res.status_code == 200
    assert len(id_res.json()["data"]["variants"]) == 3


@pytest.mark.asyncio
async def test_create_product_with_initial_variants_inline(client: AsyncClient) -> None:
    """Test creating a product and initial variants in a single atomic POST request."""
    payload = {
        "name": "Hoodie Classic",
        "slug": "hoodie-classic",
        "is_published": True,
        "variants": [
            {"sku": "HD-BLK-S", "name": "Black / Small", "price_amount": "45.00", "currency": "USD"},
            {"sku": "HD-BLK-M", "name": "Black / Medium", "price_amount": "47.50", "currency": "USD"},
        ],
    }
    response = await client.post("/api/v1/products", json=payload)
    assert response.status_code == 201
    data = response.json()["data"]
    assert data["name"] == "Hoodie Classic"
    assert len(data["variants"]) == 2

    variant_skus = [v["sku"] for v in data["variants"]]
    assert "HD-BLK-S" in variant_skus
    assert "HD-BLK-M" in variant_skus


@pytest.mark.asyncio
async def test_duplicate_sku_conflict_returns_409(client: AsyncClient) -> None:
    """Test that creating two variants with the identical SKU triggers 409 Conflict."""
    # 1. Create product 1 and add variant with SKU 'SKU-DUPLICATE-TEST'
    prod1_res = await client.post("/api/v1/products", json={"name": "Product 1", "slug": "prod-1"})
    assert prod1_res.status_code == 201
    prod1_id = prod1_res.json()["data"]["id"]

    var1_payload = {
        "sku": "SKU-DUPLICATE-TEST",
        "name": "Variant Original",
        "price_amount": "10.00",
        "currency": "USD",
    }
    var1_res = await client.post(f"/api/v1/products/{prod1_id}/variants", json=var1_payload)
    assert var1_res.status_code == 201

    # 2. Attempt to add variant with same SKU to product 1
    dup_res = await client.post(f"/api/v1/products/{prod1_id}/variants", json=var1_payload)
    assert dup_res.status_code == 409
    dup_error = dup_res.json()
    assert dup_error["error_code"] == "DUPLICATE_ENTITY"
    assert "already exists" in dup_error["detail"]

    # 3. Attempt to add same SKU to a different product (prod2) — SKU must be globally unique
    prod2_res = await client.post("/api/v1/products", json={"name": "Product 2", "slug": "prod-2"})
    assert prod2_res.status_code == 201
    prod2_id = prod2_res.json()["data"]["id"]

    cross_prod_dup = await client.post(f"/api/v1/products/{prod2_id}/variants", json=var1_payload)
    assert cross_prod_dup.status_code == 409
    assert cross_prod_dup.json()["error_code"] == "DUPLICATE_ENTITY"


@pytest.mark.asyncio
async def test_duplicate_sku_database_unique_constraint(db_session: AsyncSession) -> None:
    """Test that the database unique index on product_variants.sku raises IntegrityError on violation."""
    # 1. Seed a product directly into the database session
    product = ProductModel(name="Direct DB Product", slug="direct-db-prod", is_published=True)
    db_session.add(product)
    await db_session.flush()

    # 2. Add first variant with unique SKU
    variant1 = ProductVariantModel(
        product_id=product.id,
        sku="DB-UNIQUE-SKU",
        name="Variant 1",
        price_amount=Decimal("15.99"),
        currency="USD",
    )
    db_session.add(variant1)
    await db_session.commit()

    # 3. Attempt to insert second variant with identical SKU directly into session
    variant2 = ProductVariantModel(
        product_id=product.id,
        sku="DB-UNIQUE-SKU",
        name="Variant 2 Duplicate",
        price_amount=Decimal("18.99"),
        currency="USD",
    )
    db_session.add(variant2)

    # 4. Verify IntegrityError is raised when committing duplicate SKU
    with pytest.raises(IntegrityError):
        await db_session.commit()

    # Clean up rollback
    await db_session.rollback()


@pytest.mark.asyncio
async def test_create_variant_nonexistent_product_returns_404(client: AsyncClient) -> None:
    """Test that creating a variant for a nonexistent product ID returns 404 Not Found."""
    payload = {
        "sku": "NONEXISTENT-SKU",
        "name": "Ghost Variant",
        "price_amount": "9.99",
        "currency": "USD",
    }
    res = await client.post("/api/v1/products/nonexistent-prod-id-12345/variants", json=payload)
    assert res.status_code == 404
    error = res.json()
    assert error["error_code"] == "ENTITY_NOT_FOUND"


@pytest.mark.asyncio
async def test_selectinload_eager_loading_prevents_detached_instance_error(
    db_session: AsyncSession,
) -> None:
    """Test that ProductRepository.get_by_slug uses selectinload so variants are loaded immediately."""
    # 1. Create product and 2 variants
    product = ProductModel(name="Eager Loading Test", slug="eager-loading-test", is_published=True)
    db_session.add(product)
    await db_session.flush()

    v1 = ProductVariantModel(
        product_id=product.id,
        sku="EAGER-SKU-1",
        name="Eager Variant 1",
        price_amount=Decimal("29.99"),
        currency="USD",
    )
    v2 = ProductVariantModel(
        product_id=product.id,
        sku="EAGER-SKU-2",
        name="Eager Variant 2",
        price_amount=Decimal("39.99"),
        currency="USD",
    )
    db_session.add_all([v1, v2])
    await db_session.commit()

    # 2. Query via ProductRepository using get_by_slug (which uses selectinload)
    repo = ProductRepository(db_session)
    fetched_product = await repo.get_by_slug("eager-loading-test")
    assert fetched_product is not None

    # 3. Access product.variants — this must NOT trigger lazy-loading or MissingGreenlet
    assert len(fetched_product.variants) == 2
    skus = {v.sku for v in fetched_product.variants}
    assert skus == {"EAGER-SKU-1", "EAGER-SKU-2"}
