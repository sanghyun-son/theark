"""Database connection interface."""

from abc import ABC, abstractmethod
from types import TracebackType
from typing import Any

from core.log import get_logger
from core.types import DatabaseParamType

logger = get_logger(__name__)


class DatabaseConnection(ABC):
    """Abstract database connection interface."""

    def __init__(self, connection_string: str, **kwargs: Any) -> None:
        """Initialize database connection.

        Args:
            connection_string: Database connection string
            **kwargs: Additional connection parameters
        """
        self.connection_string = connection_string
        self.connection_params = kwargs
        self._connection: Any = None
        self._is_connected = False

    @abstractmethod
    async def connect(self) -> None:
        """Establish database connection."""
        pass

    @abstractmethod
    async def disconnect(self) -> None:
        """Close database connection."""
        pass

    @abstractmethod
    async def execute(
        self,
        query: str,
        params: DatabaseParamType = None,
    ) -> Any:
        """Execute a query.

        Args:
            query: SQL query or operation
            params: Query parameters

        Returns:
            Query result (cursor, result object, etc.)
        """
        pass

    @abstractmethod
    async def fetch_one(
        self,
        query: str,
        params: DatabaseParamType = None,
    ) -> dict[str, Any] | None:
        """Fetch single row.

        Args:
            query: SQL query
            params: Query parameters

        Returns:
            Single row as dictionary or None if not found
        """
        pass

    @abstractmethod
    async def fetch_all(
        self,
        query: str,
        params: DatabaseParamType = None,
    ) -> list[dict[str, Any]]:
        """Fetch all rows.

        Args:
            query: SQL query
            params: Query parameters

        Returns:
            List of rows as dictionaries
        """
        pass

    @abstractmethod
    async def begin_transaction(self) -> "DatabaseTransaction":
        """Begin a new transaction.

        Returns:
            Transaction object
        """
        pass

    @property
    def is_connected(self) -> bool:
        """Check if connection is active."""
        return self._is_connected

    async def __aenter__(self) -> "DatabaseConnection":
        """Async context manager entry."""
        await self.connect()
        return self

    async def __aexit__(
        self,
        exc_type: type[BaseException] | None,
        exc_val: BaseException | None,
        exc_tb: TracebackType | None,
    ) -> None:
        """Async context manager exit."""
        await self.disconnect()


class DatabaseTransaction(ABC):
    """Abstract database transaction interface."""

    def __init__(self, connection: DatabaseConnection) -> None:
        """Initialize transaction.

        Args:
            connection: Database connection
        """
        self.connection = connection
        self._transaction: Any = None

    @abstractmethod
    async def commit(self) -> None:
        """Commit the transaction."""
        pass

    @abstractmethod
    async def rollback(self) -> None:
        """Rollback the transaction."""
        pass

    async def __aenter__(self) -> "DatabaseTransaction":
        """Async context manager entry."""
        return self

    async def __aexit__(
        self,
        exc_type: type[BaseException] | None,
        exc_val: BaseException | None,
        exc_tb: TracebackType | None,
    ) -> None:
        """Async context manager exit."""
        if exc_type is None:
            await self.commit()
        else:
            await self.rollback()
