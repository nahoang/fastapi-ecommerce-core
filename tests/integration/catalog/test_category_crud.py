"""Integration tests for Category CRUD API endpoints.

Tests the full lifecycle of category entities through the HTTP interface:
- Creation of top-level root categories and child subcategories.
- Flat list retrieval with pagination.
- Individual category lookup by slug and identifier.
- Validation, duplicate constraint, and parent foreign-key error handling.
"""

import pytest
from httpx import AsyncClient


@pytest.mark.asyncio
async def test_create_category_hierarchy_and_read(client: AsyncClient) -> None:
    """Test creating parent category, child category, listing both, and fetching detail."""
    # 1. Create root parent category: "Thời trang" (slug: "thoi-trang")
    parent_payload = {
        "name": "Thời trang",
        "slug": "thoi-trang",
        "is_active": True,
    }
    parent_res = await client.post("/api/v1/categories", json=parent_payload)
    assert parent_res.status_code == 201
    parent_json = parent_res.json()
    assert parent_json["message"] == "Category created successfully"
    parent_data = parent_json["data"]
    assert parent_data["name"] == "Thời trang"
    assert parent_data["slug"] == "thoi-trang"
    assert parent_data["parent_id"] is None
    assert parent_data["is_active"] is True
    assert "id" in parent_data
    assert "created_at" in parent_data
    assert "updated_at" in parent_data
    parent_id = parent_data["id"]

    # 2. Create child category: "Đồ Nam" with parent_id pointing to "Thời trang"
    child_payload = {
        "name": "Đồ Nam",
        "slug": "do-nam",
        "parent_id": parent_id,
        "is_active": True,
    }
    child_res = await client.post("/api/v1/categories", json=child_payload)
    assert child_res.status_code == 201
    child_json = child_res.json()
    child_data = child_json["data"]
    assert child_data["name"] == "Đồ Nam"
    assert child_data["slug"] == "do-nam"
    assert child_data["parent_id"] == parent_id
    assert child_data["is_active"] is True

    # 3. GET flat list of categories -> must return both categories
    list_res = await client.get("/api/v1/categories")
    assert list_res.status_code == 200
    list_json = list_res.json()
    assert list_json["message"] == "Categories retrieved successfully"
    categories = list_json["data"]
    assert len(categories) == 2
    category_slugs = [c["slug"] for c in categories]
    assert "thoi-trang" in category_slugs
    assert "do-nam" in category_slugs

    # 4. GET category detail for "Đồ Nam" by slug -> verify correct info and parent_id
    detail_res = await client.get("/api/v1/categories/do-nam")
    assert detail_res.status_code == 200
    detail_json = detail_res.json()
    detail_data = detail_json["data"]
    assert detail_data["name"] == "Đồ Nam"
    assert detail_data["slug"] == "do-nam"
    assert detail_data["parent_id"] == parent_id
    assert detail_data["is_active"] is True


@pytest.mark.asyncio
async def test_create_category_auto_generates_slug(client: AsyncClient) -> None:
    """Test that omitting slug automatically creates a URL-friendly slug from name."""
    payload = {"name": "Giày & Dép Nam"}
    response = await client.post("/api/v1/categories", json=payload)
    assert response.status_code == 201
    data = response.json()["data"]
    assert data["name"] == "Giày & Dép Nam"
    assert data["slug"] == "giay-dep-nam"
    assert data["parent_id"] is None
    assert data["is_active"] is True


@pytest.mark.asyncio
async def test_create_category_duplicate_slug_conflict(client: AsyncClient) -> None:
    """Test that creating a category with an already existing slug returns 409 Conflict."""
    payload = {"name": "Books", "slug": "books"}
    res1 = await client.post("/api/v1/categories", json=payload)
    assert res1.status_code == 201

    # Second creation with identical slug must fail with 409 Conflict
    res2 = await client.post("/api/v1/categories", json=payload)
    assert res2.status_code == 409
    error_data = res2.json()
    assert error_data["error_code"] == "DUPLICATE_ENTITY"
    assert "already exists" in error_data["detail"]


@pytest.mark.asyncio
async def test_create_category_nonexistent_parent_id(client: AsyncClient) -> None:
    """Test that providing an invalid parent_id returns 404 Not Found."""
    payload = {
        "name": "Subcategory",
        "slug": "sub-cat",
        "parent_id": "nonexistent_parent_id_1234567890",
    }
    response = await client.post("/api/v1/categories", json=payload)
    assert response.status_code == 404
    error_data = response.json()
    assert error_data["error_code"] == "ENTITY_NOT_FOUND"


@pytest.mark.asyncio
async def test_get_nonexistent_category_by_slug(client: AsyncClient) -> None:
    """Test retrieving a category by a slug that does not exist returns 404 Not Found."""
    response = await client.get("/api/v1/categories/unknown-slug")
    assert response.status_code == 404
    error_data = response.json()
    assert error_data["error_code"] == "ENTITY_NOT_FOUND"


@pytest.mark.asyncio
async def test_category_list_pagination(client: AsyncClient) -> None:
    """Test pagination support with limit and offset query parameters."""
    # Seed 3 categories
    for i in range(1, 4):
        await client.post(
            "/api/v1/categories",
            json={"name": f"Category {i}", "slug": f"cat-{i}"},
        )

    # Fetch page with limit=2, offset=0
    res_page1 = await client.get("/api/v1/categories?limit=2&offset=0")
    assert res_page1.status_code == 200
    data_page1 = res_page1.json()["data"]
    assert len(data_page1) == 2

    # Fetch page with limit=2, offset=2
    res_page2 = await client.get("/api/v1/categories?limit=2&offset=2")
    assert res_page2.status_code == 200
    data_page2 = res_page2.json()["data"]
    assert len(data_page2) == 1
