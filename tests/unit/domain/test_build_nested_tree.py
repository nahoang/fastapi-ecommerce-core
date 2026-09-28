"""Unit tests for category nested tree builder utility.

Tests the pure Python build_nested_tree function across all scenarios:
- Empty input collections
- Single root category nodes
- Multi-level parent-child-grandchild hierarchies
- Multiple sibling categories and multiple distinct root trees
- Subtree slices where the root node has an external/orphan parent_id
- Arbitrary input ordering (children before parents)
- Polymorphic inputs (dictionaries, dataclasses, ORM models)
"""

from src.domain.catalog.category import Category
from src.domain.catalog.tree import build_nested_tree
from src.infrastructure.catalog.category_model import CategoryModel


def test_build_nested_tree_empty() -> None:
    """An empty category sequence must return an empty list."""
    assert build_nested_tree([]) == []


def test_build_nested_tree_single_root() -> None:
    """A single top-level category returns a single node with an empty children list."""
    flat_data = [
        {"id": "cat-1", "name": "Fashion", "slug": "fashion", "parent_id": None}
    ]
    tree = build_nested_tree(flat_data)

    assert len(tree) == 1
    assert tree[0]["id"] == "cat-1"
    assert tree[0]["name"] == "Fashion"
    assert tree[0]["parent_id"] is None
    assert tree[0]["children"] == []


def test_build_nested_tree_multi_level_hierarchy() -> None:
    """Verify deep hierarchy: Fashion -> Men -> T-Shirts."""
    flat_data = [
        {"id": "1", "name": "Fashion", "parent_id": None},
        {"id": "2", "name": "Men", "parent_id": "1"},
        {"id": "3", "name": "T-Shirts", "parent_id": "2"},
    ]
    tree = build_nested_tree(flat_data)

    assert len(tree) == 1
    root = tree[0]
    assert root["name"] == "Fashion"
    assert len(root["children"]) == 1

    child = root["children"][0]
    assert child["name"] == "Men"
    assert len(child["children"]) == 1

    grandchild = child["children"][0]
    assert grandchild["name"] == "T-Shirts"
    assert grandchild["children"] == []


def test_build_nested_tree_multiple_roots_and_siblings() -> None:
    """Verify multiple roots (Fashion, Electronics) with multiple sibling children."""
    flat_data = [
        {"id": "1", "name": "Fashion", "parent_id": None},
        {"id": "2", "name": "Electronics", "parent_id": None},
        {"id": "11", "name": "Men", "parent_id": "1"},
        {"id": "12", "name": "Women", "parent_id": "1"},
        {"id": "21", "name": "Laptops", "parent_id": "2"},
        {"id": "22", "name": "Phones", "parent_id": "2"},
    ]
    tree = build_nested_tree(flat_data)

    assert len(tree) == 2
    root_names = [r["name"] for r in tree]
    assert root_names == ["Fashion", "Electronics"]

    fashion_children = [c["name"] for c in tree[0]["children"]]
    assert fashion_children == ["Men", "Women"]

    electronics_children = [c["name"] for c in tree[1]["children"]]
    assert electronics_children == ["Laptops", "Phones"]


def test_build_nested_tree_subtree_with_orphan_parent() -> None:
    """When a subtree is passed where the root has a parent_id outside the dataset,

    that node must be correctly treated as a root of the returned tree.
    """
    flat_data = [
        {"id": "2", "name": "Men", "parent_id": "1"},  # Parent '1' is not in this dataset
        {"id": "3", "name": "T-Shirts", "parent_id": "2"},
        {"id": "4", "name": "Jeans", "parent_id": "2"},
    ]
    tree = build_nested_tree(flat_data)

    assert len(tree) == 1
    assert tree[0]["name"] == "Men"
    assert len(tree[0]["children"]) == 2
    children_names = [c["name"] for c in tree[0]["children"]]
    assert "T-Shirts" in children_names
    assert "Jeans" in children_names


def test_build_nested_tree_arbitrary_order() -> None:
    """Tree construction should be robust to order: children appear before parents."""
    flat_data = [
        {"id": "3", "name": "T-Shirts", "parent_id": "2"},
        {"id": "2", "name": "Men", "parent_id": "1"},
        {"id": "1", "name": "Fashion", "parent_id": None},
    ]
    tree = build_nested_tree(flat_data)

    assert len(tree) == 1
    assert tree[0]["name"] == "Fashion"
    assert tree[0]["children"][0]["name"] == "Men"
    assert tree[0]["children"][0]["children"][0]["name"] == "T-Shirts"


def test_build_nested_tree_with_domain_entities_and_orm_models() -> None:
    """Verify build_nested_tree works seamlessly with Category dataclasses and CategoryModel ORM instances."""
    # Mix of Domain Dataclass Entity and ORM Model
    c1 = Category(id="1", name="Fashion", slug="fashion", parent_id=None)
    c2 = CategoryModel(id="2", name="Men", slug="men", parent_id="1")
    c3 = Category(id="3", name="T-Shirts", slug="t-shirts", parent_id="2")

    tree = build_nested_tree([c1, c2, c3])

    assert len(tree) == 1
    assert tree[0]["name"] == "Fashion"
    assert tree[0]["children"][0]["name"] == "Men"
    assert tree[0]["children"][0]["children"][0]["name"] == "T-Shirts"
