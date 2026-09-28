"""Integration tests for Product CRUD API endpoints.

Tests the full lifecycle of product entities through the HTTP interface:
- Creation of products with and without category links.
- Detail lookup by unique URL slug and UUID primary key.
- Paginated listing with limit and offset query parameters.
- Verification of has_next pagination flags.
- Validation, duplicate slug conflict, and foreign key error handling.
"""

import pytest
from httpx import AsyncClient


@pytest.mark.asyncio
async def test_create_product_and_read_detail(client: AsyncClient) -> None:
    """Test creating a product linked to a category, then fetching its details by slug."""
    # 1. Create a parent category first
    category_payload = {
        "name": "Electronics",
        "slug": "electronics",
        "is_active": True,
    }
    cat_res = await client.post("/api/v1/categories", json=category_payload)
    assert cat_res.status_code == 201
    category_id = cat_res.json()["data"]["id"]

    # 2. Create a product linked to the category
    product_payload = {
        "name": "Wireless Noise Cancelling Headphones",
        "slug": "wireless-headphones",
        "category_id": category_id,
        "description": "High-fidelity sound with 40-hour battery life.",
        "is_published": True,
    }
    create_res = await client.post("/api/v1/products", json=product_payload)
    assert create_res.status_code == 201
    create_json = create_res.json()
    assert create_json["message"] == "Product created successfully"
    product_data = create_json["data"]
    assert product_data["name"] == "Wireless Noise Cancelling Headphones"
    assert product_data["slug"] == "wireless-headphones"
    assert product_data["category_id"] == category_id
    assert product_data["description"] == "High-fidelity sound with 40-hour battery life."
    assert product_data["is_published"] is True
    assert "id" in product_data
    assert "created_at" in product_data
    assert "updated_at" in product_data
    product_id = product_data["id"]

    # 3. Retrieve product details by slug
    detail_res = await client.get("/api/v1/products/wireless-headphones")
    assert detail_res.status_code == 200
    detail_json = detail_res.json()
    assert detail_json["message"] == "Product retrieved successfully"
    detail_data = detail_json["data"]
    assert detail_data["id"] == product_id
    assert detail_data["name"] == "Wireless Noise Cancelling Headphones"
    assert detail_data["slug"] == "wireless-headphones"
    assert detail_data["category_id"] == category_id
    assert detail_data["description"] == "High-fidelity sound with 40-hour battery life."
    assert detail_data["is_published"] is True

    # 4. Also verify secondary lookup by ID
    id_res = await client.get(f"/api/v1/products/{product_id}")
    assert id_res.status_code == 200
    assert id_res.json()["data"]["slug"] == "wireless-headphones"


@pytest.mark.asyncio
async def test_product_list_pagination(client: AsyncClient) -> None:
    """Test creating 5 products and validating paginated listing with limit=2."""
    # 1. Seed 5 products into the catalog
    for i in range(1, 6):
        payload = {
            "name": f"Product Item {i}",
            "slug": f"product-item-{i}",
            "description": f"Description for product {i}",
            "is_published": True,
        }
        res = await client.post("/api/v1/products", json=payload)
        assert res.status_code == 201

    # 2. Fetch page 1: limit=2, offset=0
    # Expected: 2 items, total=5, page=1, page_size=2, has_next=True (since 1 * 2 < 5)
    page1_res = await client.get("/api/v1/products?limit=2&offset=0")
    assert page1_res.status_code == 200
    page1_data = page1_res.json()
    assert page1_data["total"] == 5
    assert page1_data["page"] == 1
    assert page1_data["page_size"] == 2
    assert page1_data["has_next"] is True
    assert len(page1_data["data"]) == 2

    # 3. Fetch page 2: limit=2, offset=2
    # Expected: 2 items, total=5, page=2, page_size=2, has_next=True (since 2 * 2 < 5)
    page2_res = await client.get("/api/v1/products?limit=2&offset=2")
    assert page2_res.status_code == 200
    page2_data = page2_res.json()
    assert page2_data["total"] == 5
    assert page2_data["page"] == 2
    assert page2_data["page_size"] == 2
    assert page2_data["has_next"] is True
    assert len(page2_data["data"]) == 2

    # 4. Fetch page 3: limit=2, offset=4
    # Expected: 1 item, total=5, page=3, page_size=2, has_next=False (since 3 * 2 >= 5)
    page3_res = await client.get("/api/v1/products?limit=2&offset=4")
    assert page3_res.status_code == 200
    page3_data = page3_res.json()
    assert page3_data["total"] == 5
    assert page3_data["page"] == 3
    assert page3_data["page_size"] == 2
    assert page3_data["has_next"] is False
    assert len(page3_data["data"]) == 1


@pytest.mark.asyncio
async def test_create_product_auto_generates_slug(client: AsyncClient) -> None:
    """Test that omitting slug automatically creates a URL-friendly slug from name."""
    payload = {
        "name": "Áo Thun Cotton Nam",
        "description": "100% organic cotton t-shirt.",
    }
    response = await client.post("/api/v1/products", json=payload)
    assert response.status_code == 201
    data = response.json()["data"]
    assert data["name"] == "Áo Thun Cotton Nam"
    assert data["slug"] == "ao-thun-cotton-nam"
    assert data["category_id"] is None
    assert data["is_published"] is False


@pytest.mark.asyncio
async def test_create_product_duplicate_slug_conflict(client: AsyncClient) -> None:
    """Test that creating a product with an already existing slug returns 409 Conflict."""
    payload = {"name": "Running Shoes", "slug": "running-shoes"}
    res1 = await client.post("/api/v1/products", json=payload)
    assert res1.status_code == 201

    # Second creation with the exact same slug must trigger 409 Conflict
    res2 = await client.post("/api/v1/products", json=payload)
    assert res2.status_code == 409
    error_data = res2.json()
    assert error_data["error_code"] == "DUPLICATE_ENTITY"
    assert "already exists" in error_data["detail"]


@pytest.mark.asyncio
async def test_create_product_invalid_category_id(client: AsyncClient) -> None:
    """Test that specifying a non-existent category_id returns 404 Not Found."""
    payload = {
        "name": "Invalid Category Product",
        "slug": "invalid-cat-prod",
        "category_id": "nonexistent_category_uuid_123456",
    }
    response = await client.post("/api/v1/products", json=payload)
    assert response.status_code == 404
    error_data = response.json()
    assert error_data["error_code"] == "ENTITY_NOT_FOUND"


@pytest.mark.asyncio
async def test_get_nonexistent_product_by_slug(client: AsyncClient) -> None:
    """Test retrieving a product by unknown slug returns 404 Not Found."""
    response = await client.get("/api/v1/products/does-not-exist-slug")
    assert response.status_code == 404
    error_data = response.json()
    assert error_data["error_code"] == "ENTITY_NOT_FOUND"
