"""Tree building utilities for hierarchical catalog domain entities.

This module provides pure Python algorithms for transforming flat sequences
of categories into nested tree structures with parent-child relationships.
Being part of the pure Domain layer, it maintains zero external framework
dependencies (no FastAPI, no SQLAlchemy).
"""

from dataclasses import asdict, is_dataclass
from typing import Any, Sequence


def _to_node_dict(item: Any) -> dict[str, Any]:
    """Normalize an arbitrary category representation into a standard dictionary.

    Extracts entity attributes from dictionaries, dataclasses, ORM models,
    or Pydantic schemas, and guarantees a new, empty 'children' list is present.

    Args:
        item: Category data representation (dict, ORM model, dataclass, etc.).

    Returns:
        A shallow dictionary representation with an empty 'children' list.
    """
    if isinstance(item, dict):
        node = dict(item)
    elif hasattr(item, "model_dump") and callable(item.model_dump):
        # Pydantic v2 BaseSchema or DTO
        node = item.model_dump()
    elif is_dataclass(item) and not isinstance(item, type):
        # Python standard dataclass (e.g. Domain Entity)
        node = asdict(item)
    elif hasattr(item, "__table__"):
        # SQLAlchemy 2.0 ORM model instance (e.g. CategoryModel)
        node = {c.name: getattr(item, c.name) for c in item.__table__.columns}
    elif hasattr(item, "__dict__"):
        # Generic Python object, ignoring internal private attributes
        node = {k: v for k, v in item.__dict__.items() if not k.startswith("_")}
    else:
        # Fallback to direct attribute extraction
        node = {
            "id": getattr(item, "id", None),
            "parent_id": getattr(item, "parent_id", None),
        }

    # Ensure children list is initialized freshly for building the tree
    node["children"] = []
    return node


def build_nested_tree(flat_categories: Sequence[Any]) -> list[dict[str, Any]]:
    """Transform a flat list of categories into a nested hierarchical tree.

    Implements a single-pass hash map algorithm with O(N) linear time complexity
    and O(N) auxiliary space:
    1. First pass: Register all nodes in an id-to-node lookup dictionary.
    2. Second pass: Traverse nodes and attach children to their respective parents.
       Nodes with parent_id IS NULL or whose parent does not exist in the flat
       sequence (such as when querying a subtree) are collected as root nodes.

    Args:
        flat_categories: Sequence of category items in flat order.

    Returns:
        List of root node dictionaries, each containing recursive 'children' lists.
    """
    if not flat_categories:
        return []

    # Map category string ID to mutable node dictionary for O(1) parent lookups
    node_map: dict[str, dict[str, Any]] = {}
    for item in flat_categories:
        node = _to_node_dict(item)
        node_id = str(node.get("id"))
        node_map[node_id] = node

    roots: list[dict[str, Any]] = []

    # Second pass: wire parent-child relationships
    for node in node_map.values():
        parent_id = node.get("parent_id")
        parent_id_str = str(parent_id) if parent_id is not None else None

        if parent_id_str is not None and parent_id_str in node_map:
            # Parent exists in current dataset: attach as child
            node_map[parent_id_str]["children"].append(node)
        else:
            # No parent or parent outside current dataset: treat as root
            roots.append(node)

    return roots
