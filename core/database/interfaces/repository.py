"""Repository interface for database operations."""

from abc import ABC, abstractmethod
from typing import Any, Generic, TypeVar

from core.database.interfaces.connection import DatabaseConnection

T = TypeVar("T")


class Repository(ABC, Generic[T]):
    """Generic repository interface for database operations."""

    def __init__(self, connection: DatabaseConnection) -> None:
        """Initialize repository with database connection.

        Args:
            connection: Database connection instance
        """
        self.connection = connection

    @abstractmethod
    async def create(self, entity: T) -> int:
        """Create entity and return ID.

        Args:
            entity: Entity to create

        Returns:
            Created entity ID
        """
        pass

    @abstractmethod
    async def get_by_id(self, entity_id: int) -> T | None:
        """Get entity by ID.

        Args:
            entity_id: Entity ID

        Returns:
            Entity instance or None if not found
        """
        pass

    @abstractmethod
    async def update(self, entity: T) -> bool:
        """Update entity.

        Args:
            entity: Entity to update

        Returns:
            True if updated successfully, False otherwise
        """
        pass

    @abstractmethod
    async def delete(self, entity_id: int) -> bool:
        """Delete entity by ID.

        Args:
            entity_id: Entity ID to delete

        Returns:
            True if deleted successfully, False otherwise
        """
        pass

    @abstractmethod
    async def get_all(
        self, limit: int = 100, offset: int = 0, **filters: Any
    ) -> list[T]:
        """List entities with pagination and filters.

        Args:
            limit: Maximum number of results
            offset: Number of results to skip
            **filters: Additional filter criteria

        Returns:
            List of entities
        """
        pass

    @abstractmethod
    async def count(self, **filters: Any) -> int:
        """Count entities matching filters.

        Args:
            **filters: Filter criteria

        Returns:
            Number of matching entities
        """
        pass

    @abstractmethod
    async def exists(self, entity_id: int) -> bool:
        """Check if entity exists.

        Args:
            entity_id: Entity ID to check

        Returns:
            True if entity exists, False otherwise
        """
        pass

    @abstractmethod
    async def find_one(self, **filters: Any) -> T | None:
        """Find single entity matching filters.

        Args:
            **filters: Filter criteria

        Returns:
            Entity instance or None if not found
        """
        pass

    @abstractmethod
    async def find_all(self, **filters: Any) -> list[T]:
        """Find all entities matching filters.

        Args:
            **filters: Filter criteria

        Returns:
            List of matching entities
        """
        pass


class QueryBuilder(ABC):
    """Abstract query builder interface."""

    @abstractmethod
    def select(self, *columns: str) -> "QueryBuilder":
        """Set SELECT clause."""
        pass

    @abstractmethod
    def from_table(self, table: str) -> "QueryBuilder":
        """Set FROM clause."""
        pass

    @abstractmethod
    def where(self, condition: str, *params: Any) -> "QueryBuilder":
        """Add WHERE condition."""
        pass

    @abstractmethod
    def order_by(self, column: str, direction: str = "ASC") -> "QueryBuilder":
        """Add ORDER BY clause."""
        pass

    @abstractmethod
    def limit(self, limit: int) -> "QueryBuilder":
        """Set LIMIT clause."""
        pass

    @abstractmethod
    def offset(self, offset: int) -> "QueryBuilder":
        """Set OFFSET clause."""
        pass

    @abstractmethod
    def build(self) -> tuple[str, tuple[Any, ...]]:
        """Build the final query.

        Returns:
            Tuple of (query_string, parameters)
        """
        pass


class RepositoryFactory(ABC):
    """Abstract repository factory interface."""

    @abstractmethod
    def create_repository(
        self,
        entity_type: type[T],
        connection: DatabaseConnection,
    ) -> Repository[T]:
        """Create repository for entity type.

        Args:
            entity_type: Type of entity
            connection: Database connection

        Returns:
            Repository instance
        """
        pass
