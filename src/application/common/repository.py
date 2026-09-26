"""Abstract repository interface for application layer.

This module defines the abstract generic repository contract (IRepository).
Following Clean Architecture and the Dependency Inversion Principle (DIP),
the application and domain layers depend solely on this pure Python abstraction,
completely decoupled from any database engine or ORM implementation (e.g. SQLAlchemy).
"""

from abc import ABC, abstractmethod
from typing import Generic, TypeVar

# T represents the generic domain entity or model managed by the repository.
# A TypeVar allows IRepository to remain strictly type-safe for any entity type.
T = TypeVar("T")


class IRepository(ABC, Generic[T]):
    """Abstract generic repository interface defining standard asynchronous CRUD operations.

    Any persistence mechanism (SQLAlchemy, in-memory, NoSQL, etc.) must implement
    this interface to be utilized by application use cases and domain services.
    """

    @abstractmethod
    async def get_by_id(self, id: str) -> T | None:
        """Retrieve a single entity by its unique identifier.

        Args:
            id: The unique primary key identifier string.

        Returns:
            The entity instance if found, or None if no matching record exists.
        """
        raise NotImplementedError

    @abstractmethod
    async def list_all(self, limit: int = 20, offset: int = 0) -> list[T]:
        """Retrieve a paginated collection of entities.

        Args:
            limit: Maximum number of records to return (pagination limit, default: 20).
            offset: Number of records to skip before returning results (pagination offset, default: 0).

        Returns:
            A list containing the retrieved entities.
        """
        raise NotImplementedError

    @abstractmethod
    async def add(self, entity: T) -> T:
        """Persist a new entity into the storage.

        Args:
            entity: The entity instance to add.

        Returns:
            The persisted entity instance, potentially populated with generated keys or defaults.
        """
        raise NotImplementedError

    @abstractmethod
    async def update(self, entity: T) -> T:
        """Persist modifications made to an existing entity.

        Args:
            entity: The modified entity instance.

        Returns:
            The updated persistent entity instance.
        """
        raise NotImplementedError

    @abstractmethod
    async def delete(self, id: str) -> None:
        """Remove an entity by its unique identifier.

        Args:
            id: The unique primary key identifier string of the entity to remove.
        """
        raise NotImplementedError
