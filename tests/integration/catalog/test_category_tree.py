"""Integration tests for Category Tree and Breadcrumbs API endpoints.

Tests hierarchical queries powered by SQL Recursive Common Table Expressions (CTEs):
- Building full nested category trees (parent -> children -> grandchildren).
- Subtree queries starting at a specific intermediate category node.
- Upward breadcrumbs retrieval from leaf to root (e.g. Thời trang > Đồ Nam > Áo thun).
- Proper 404 Not Found error handling for invalid or nonexistent category slugs/IDs.
"""

import pytest
from httpx import AsyncClient


@pytest.mark.asyncio
async def test_category_tree_and_breadcrumbs_flow(client: AsyncClient) -> None:
    """Test full hierarchy creation, nested tree API retrieval, and breadcrumb path traversal.

    Hierarchy to construct:
    - "Thời trang" (root)
      └── "Đồ Nam" (child of Thời trang)
          ├── "Áo thun" (child of Đồ Nam)
          └── "Quần jeans" (child of Đồ Nam)
    """
    # 1. Create root category: "Thời trang" (slug: "thoi-trang")
    root_res = await client.post(
        "/api/v1/categories",
        json={"name": "Thời trang", "slug": "thoi-trang", "is_active": True},
    )
    assert root_res.status_code == 201
    root_id = root_res.json()["data"]["id"]

    # 2. Create child category: "Đồ Nam" (parent: "Thời trang")
    men_res = await client.post(
        "/api/v1/categories",
        json={"name": "Đồ Nam", "slug": "do-nam", "parent_id": root_id, "is_active": True},
    )
    assert men_res.status_code == 201
    men_id = men_res.json()["data"]["id"]

    # 3. Create leaf subcategory: "Áo thun" (parent: "Đồ Nam")
    tshirt_res = await client.post(
        "/api/v1/categories",
        json={"name": "Áo thun", "slug": "ao-thun", "parent_id": men_id, "is_active": True},
    )
    assert tshirt_res.status_code == 201

    # 4. Create sibling leaf subcategory: "Quần jeans" (parent: "Đồ Nam")
    jeans_res = await client.post(
        "/api/v1/categories",
        json={"name": "Quần jeans", "slug": "quan-jeans", "parent_id": men_id, "is_active": True},
    )
    assert jeans_res.status_code == 201

    # 5. GET /api/v1/categories/tree -> verify full nested tree response
    tree_res = await client.get("/api/v1/categories/tree")
    assert tree_res.status_code == 200
    tree_json = tree_res.json()
    assert tree_json["message"] == "Category tree retrieved successfully"
    roots = tree_json["data"]
    assert len(roots) == 1

    root_node = roots[0]
    assert root_node["name"] == "Thời trang"
    assert root_node["slug"] == "thoi-trang"
    assert root_node["parent_id"] is None
    assert len(root_node["children"]) == 1

    men_node = root_node["children"][0]
    assert men_node["name"] == "Đồ Nam"
    assert men_node["slug"] == "do-nam"
    assert men_node["parent_id"] == root_id
    assert len(men_node["children"]) == 2

    men_children_names = [child["name"] for child in men_node["children"]]
    assert "Áo thun" in men_children_names
    assert "Quần jeans" in men_children_names

    # 6. GET /api/v1/categories/ao-thun/breadcrumbs -> returns ["Thời trang", "Đồ Nam", "Áo thun"]
    bread_res = await client.get("/api/v1/categories/ao-thun/breadcrumbs")
    assert bread_res.status_code == 200
    bread_json = bread_res.json()
    assert bread_json["message"] == "Category breadcrumbs retrieved successfully"
    breadcrumbs = bread_json["data"]
    assert len(breadcrumbs) == 3

    breadcrumb_names = [item["name"] for item in breadcrumbs]
    assert breadcrumb_names == ["Thời trang", "Đồ Nam", "Áo thun"]

    # 7. GET /api/v1/categories/quan-jeans/breadcrumbs -> returns ["Thời trang", "Đồ Nam", "Quần jeans"]
    jeans_bread_res = await client.get("/api/v1/categories/quan-jeans/breadcrumbs")
    assert jeans_bread_res.status_code == 200
    assert [item["name"] for item in jeans_bread_res.json()["data"]] == [
        "Thời trang",
        "Đồ Nam",
        "Quần jeans",
    ]

    # 8. GET /api/v1/categories/thoi-trang/breadcrumbs (root) -> returns ["Thời trang"]
    root_bread_res = await client.get("/api/v1/categories/thoi-trang/breadcrumbs")
    assert root_bread_res.status_code == 200
    assert [item["name"] for item in root_bread_res.json()["data"]] == ["Thời trang"]


@pytest.mark.asyncio
async def test_category_subtree_query_by_root_id(client: AsyncClient) -> None:
    """Test retrieving a subtree starting from an intermediate category."""
    # 1. Setup hierarchy: Electronics -> Laptops -> Gaming Laptops
    e_res = await client.post("/api/v1/categories", json={"name": "Electronics", "slug": "electronics"})
    e_id = e_res.json()["data"]["id"]

    l_res = await client.post("/api/v1/categories", json={"name": "Laptops", "slug": "laptops", "parent_id": e_id})
    l_id = l_res.json()["data"]["id"]

    await client.post("/api/v1/categories", json={"name": "Gaming", "slug": "gaming", "parent_id": l_id})

    # 2. Query subtree starting from 'Laptops' using root_id query parameter
    subtree_res = await client.get(f"/api/v1/categories/tree?root_id={l_id}")
    assert subtree_res.status_code == 200
    subtree_data = subtree_res.json()["data"]

    # Root of this subtree should be 'Laptops'
    assert len(subtree_data) == 1
    assert subtree_data[0]["name"] == "Laptops"
    assert len(subtree_data[0]["children"]) == 1
    assert subtree_data[0]["children"][0]["name"] == "Gaming"


@pytest.mark.asyncio
async def test_breadcrumbs_nonexistent_category_returns_404(client: AsyncClient) -> None:
    """Requesting breadcrumbs for a nonexistent category slug must return 404 Not Found."""
    response = await client.get("/api/v1/categories/nonexistent-category/breadcrumbs")
    assert response.status_code == 404
    error_json = response.json()
    assert error_json["error_code"] == "ENTITY_NOT_FOUND"


@pytest.mark.asyncio
async def test_tree_nonexistent_root_id_returns_404(client: AsyncClient) -> None:
    """Requesting category tree with a nonexistent root_id must return 404 Not Found."""
    response = await client.get("/api/v1/categories/tree?root_id=nonexistent-id")
    assert response.status_code == 404
    error_json = response.json()
    assert error_json["error_code"] == "ENTITY_NOT_FOUND"
