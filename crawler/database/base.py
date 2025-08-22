"""Abstract base class for database managers."""

from abc import ABC, abstractmethod
from typing import Any

from core.log import get_logger

logger = get_logger(__name__)


class DatabaseManager(ABC):
    """Abstract base class for database managers using Strategy pattern."""

    def __init__(self, connection_string: str) -> None:
        """Initialize database manager.

        Args:
            connection_string: Database connection string
        """
        self.connection_string = connection_string
        self.logger = logger

    @abstractmethod
    def connect(self) -> None:
        """Establish database connection."""
        pass

    @abstractmethod
    def disconnect(self) -> None:
        """Close database connection."""
        pass

    @abstractmethod
    def execute(self, query: str, params: tuple[Any, ...] | None = None) -> Any:
        """Execute a database query.

        Args:
            query: SQL query string
            params: Query parameters

        Returns:
            Query result
        """
        pass

    @abstractmethod
    def execute_many(
        self, query: str, params_list: list[tuple[Any, ...]]
    ) -> None:
        """Execute a query with multiple parameter sets.

        Args:
            query: SQL query string
            params_list: List of parameter tuples
        """
        pass

    @abstractmethod
    def fetch_one(
        self, query: str, params: tuple[Any, ...] | None = None
    ) -> tuple[Any, ...] | None:
        """Fetch a single row from the database.

        Args:
            query: SQL query string
            params: Query parameters

        Returns:
            Single row as tuple or None
        """
        pass

    @abstractmethod
    def fetch_all(
        self, query: str, params: tuple[Any, ...] | None = None
    ) -> list[tuple[Any, ...]]:
        """Fetch all rows from the database.

        Args:
            query: SQL query string
            params: Query parameters

        Returns:
            List of rows as tuples
        """
        pass

    @abstractmethod
    def create_tables(self) -> None:
        """Create all necessary database tables."""
        pass

    @abstractmethod
    def __enter__(self) -> "DatabaseManager":
        """Context manager entry."""
        pass

    @abstractmethod
    def __exit__(
        self,
        exc_type: type[BaseException] | None,
        exc_val: BaseException | None,
        exc_tb: Any,
    ) -> None:
        """Context manager exit."""
        pass
