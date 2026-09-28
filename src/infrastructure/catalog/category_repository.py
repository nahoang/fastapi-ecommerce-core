"""Category repository implementation for catalog infrastructure layer.

This module provides data access operations for CategoryModel entities,
extending the generic BaseRepository with category-specific query methods.
"""

from sqlalchemy import desc, literal, select
from sqlalchemy.ext.asyncio import AsyncSession

from src.infrastructure.catalog.category_model import CategoryModel
from src.infrastructure.database.base_repository import BaseRepository


class CategoryRepository(BaseRepository[CategoryModel]):
    """Repository handling database operations for CategoryModel entities.

    Inherits standard asynchronous CRUD operations (get_by_id, list_all, add,
    update, delete) from BaseRepository and provides hierarchical queries using
    SQL Recursive Common Table Expressions (CTEs).
    """

    def __init__(self, session: AsyncSession) -> None:
        """Initialize the category repository with an active async database session.

        Args:
            session: SQLAlchemy AsyncSession for executing asynchronous queries.
        """
        super().__init__(session, CategoryModel)

    async def get_by_slug(self, slug: str) -> CategoryModel | None:
        """Retrieve a category by its unique URL-friendly slug.

        Args:
            slug: URL-friendly identifier string (e.g. 'clothing', 'men').

        Returns:
            The CategoryModel instance if found, or None if no category matches.
        """
        # Modern SQLAlchemy 2.0 select query: select(CategoryModel).where(...)
        stmt = select(CategoryModel).where(CategoryModel.slug == slug)
        result = await self._session.execute(stmt)
        # scalar_one_or_none returns a single model instance or None if not found
        return result.scalar_one_or_none()

    async def get_tree(self, root_id: str | None = None) -> list[CategoryModel]:
        """Retrieve a category subtree or entire hierarchy using an SQL Recursive CTE.

        Executes a single database query to traverse parent-child relationships:
        1. Anchor member: selects the starting root node(s). If root_id is None,
           fetches all top-level roots (parent_id IS NULL). If root_id is provided,
           fetches that specific category node.
        2. Recursive member: joins CategoryModel child rows where child.parent_id == cte.id.
        3. Union: combines anchor and recursive members until no further children exist.

        Args:
            root_id: Optional UUID string of the subtree root. If None, fetches the entire tree.

        Returns:
            Flat list of CategoryModel instances belonging to the hierarchy.
        """
        # Step 1: Define anchor query (initial seed rows)
        if root_id is None:
            # All root categories where parent_id is NULL
            anchor = select(CategoryModel).where(CategoryModel.parent_id.is_(None))
        else:
            # Specific category serving as the subtree root
            anchor = select(CategoryModel).where(CategoryModel.id == root_id)

        # Step 2: Create Recursive Common Table Expression (CTE)
        # cte(name="category_tree", recursive=True) tells database to allow recursive self-references
        tree_cte = anchor.cte(name="category_tree", recursive=True)

        # Step 3: Define recursive member query (joining child categories)
        # CategoryModel is the child table, joining where child.parent_id matches cte.id
        recursive_part = select(CategoryModel).join(
            tree_cte, CategoryModel.parent_id == tree_cte.c.id
        )

        # Step 4: Combine anchor and recursive member using union_all
        tree_cte = tree_cte.union_all(recursive_part)

        # Step 5: Execute final query selecting all CategoryModel rows matched by the CTE
        stmt = select(CategoryModel).join(tree_cte, CategoryModel.id == tree_cte.c.id)
        result = await self._session.execute(stmt)
        return list(result.scalars().all())

    async def get_breadcrumbs(self, category_id: str) -> list[CategoryModel]:
        """Retrieve breadcrumb trail from root category down to the target category.

        Uses an SQL Recursive CTE traversing upward from child to parent:
        1. Anchor member: starts at the target category (category_id) with depth = 0.
        2. Recursive member: joins the parent category (parent.id == cte.parent_id)
           and increments depth by 1 (depth + 1).
        3. Result ordering: sorts by depth DESC so that the root ancestor (highest depth)
           appears first, followed by intermediate parents, down to the target leaf (depth 0).

        Args:
            category_id: Unique 32-character UUID string of the target category.

        Returns:
            Ordered list of CategoryModel instances: [root, ..., parent, target_category].
        """
        # Step 1: Define anchor query at the leaf/target category with depth = 0
        anchor = select(
            CategoryModel,
            literal(0).label("depth"),
        ).where(CategoryModel.id == category_id)

        # Step 2: Create Recursive CTE for upward traversal
        breadcrumbs_cte = anchor.cte(name="category_breadcrumbs", recursive=True)

        # Step 3: Define recursive member joining each category's parent
        # Join condition: CategoryModel (parent) id equals CTE row's parent_id
        # Increment depth so the top root node will have the highest depth number
        recursive_part = select(
            CategoryModel,
            (breadcrumbs_cte.c.depth + 1).label("depth"),
        ).join(breadcrumbs_cte, CategoryModel.id == breadcrumbs_cte.c.parent_id)

        # Step 4: Combine anchor and parent traversal using union_all
        breadcrumbs_cte = breadcrumbs_cte.union_all(recursive_part)

        # Step 5: Order by depth DESC to produce [root -> ... -> parent -> leaf] sequence
        stmt = (
            select(CategoryModel)
            .join(breadcrumbs_cte, CategoryModel.id == breadcrumbs_cte.c.id)
            .order_by(desc(breadcrumbs_cte.c.depth))
        )
        result = await self._session.execute(stmt)
        return list(result.scalars().all())
