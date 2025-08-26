"""Database manager interface."""

from abc import ABC, abstractmethod
from typing import Any, Type

from core.database.interfaces.connection import DatabaseConnection
from core.database.interfaces.repository import Repository, RepositoryFactory
from core.log import get_logger
from core.types import DatabaseParamType

logger = get_logger(__name__)


class DatabaseManager(ABC):
    """Abstract database manager interface."""

    def __init__(self, connection_string: str, **kwargs: Any) -> None:
        """Initialize database manager.

        Args:
            connection_string: Database connection string
            **kwargs: Additional configuration parameters
        """
        self.connection_string = connection_string
        self.config = kwargs
        self._connection: DatabaseConnection
        self._repositories: dict[Any, Repository[Any]] = {}
        self._repository_factory: RepositoryFactory | None = None

    @abstractmethod
    async def connect(self) -> None:
        """Establish database connection."""
        pass

    @abstractmethod
    async def disconnect(self) -> None:
        """Close database connection."""
        pass

    @abstractmethod
    async def create_tables(self) -> None:
        """Create database tables."""
        pass

    @abstractmethod
    async def drop_tables(self) -> None:
        """Drop database tables."""
        pass

    @abstractmethod
    async def execute(self, query: str, params: DatabaseParamType = None) -> Any:
        """Execute a query.

        Args:
            query: SQL query
            params: Query parameters

        Returns:
            Query result
        """
        pass

    @abstractmethod
    async def fetch_one(
        self, query: str, params: DatabaseParamType = None
    ) -> dict[str, Any] | None:
        """Fetch single row.

        Args:
            query: SQL query
            params: Query parameters

        Returns:
            Single row as dictionary or None
        """
        pass

    @abstractmethod
    async def fetch_all(
        self, query: str, params: DatabaseParamType = None
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
    def get_repository(self, entity_type: Type[Any]) -> Repository[Any]:
        """Get repository for entity type.

        Args:
            entity_type: Type of entity

        Returns:
            Repository instance
        """
        pass

    def set_repository_factory(self, factory: RepositoryFactory) -> None:
        """Set repository factory.

        Args:
            factory: Repository factory instance
        """
        self._repository_factory = factory

    # LLM Database Methods
    @abstractmethod
    async def track_token_usage(
        self,
        model: str,
        prompt_tokens: int,
        completion_tokens: int,
        total_tokens: int,
        cost: float | None = None,
    ) -> None:
        """Track token usage for LLM models.

        Args:
            model: Model name
            prompt_tokens: Number of prompt tokens
            completion_tokens: Number of completion tokens
            total_tokens: Total number of tokens
            cost: Cost in USD (optional)
        """
        pass

    @abstractmethod
    async def get_token_usage_stats(
        self,
        model: str | None = None,
        start_date: str | None = None,
        end_date: str | None = None,
    ) -> dict[str, Any]:
        """Get token usage statistics.

        Args:
            model: Model name filter (optional)
            start_date: Start date filter (optional)
            end_date: End date filter (optional)

        Returns:
            Token usage statistics
        """
        pass

    @abstractmethod
    async def track_request_status(
        self,
        request_id: str,
        status: str,
        model: str | None = None,
        error_message: str | None = None,
    ) -> None:
        """Track LLM request status.

        Args:
            request_id: Unique request identifier
            status: Request status
            model: Model used (optional)
            error_message: Error message if failed (optional)
        """
        pass

    @abstractmethod
    async def get_request_history(
        self, request_id: str | None = None, status: str | None = None, limit: int = 100
    ) -> list[dict[str, Any]]:
        """Get request history.

        Args:
            request_id: Request ID filter (optional)
            status: Status filter (optional)
            limit: Maximum number of records to return

        Returns:
            List of request records
        """
        pass

    @property
    def connection(self) -> DatabaseConnection | None:
        """Get database connection."""
        return self._connection

    @property
    def is_connected(self) -> bool:
        """Check if database is connected."""
        return self._connection is not None and self._connection.is_connected

    async def __aenter__(self) -> "DatabaseManager":
        """Async context manager entry."""
        await self.connect()
        return self

    async def __aexit__(
        self,
        exc_type: type[BaseException] | None,
        exc_val: BaseException | None,
        exc_tb: object,
    ) -> None:
        """Async context manager exit."""
        await self.disconnect()


class DatabaseFactory(ABC):
    """Abstract database factory interface."""

    @abstractmethod
    def create_manager(
        self,
        db_type: str,
        connection_string: str,
        **kwargs: Any,
    ) -> DatabaseManager:
        """Create database manager.

        Args:
            db_type: Database type (sqlite, postgresql, mysql, etc.)
            connection_string: Database connection string
            **kwargs: Additional configuration parameters

        Returns:
            Database manager instance
        """
        pass

    @abstractmethod
    def create_connection(
        self,
        db_type: str,
        connection_string: str,
        **kwargs: Any,
    ) -> DatabaseConnection:
        """Create database connection.

        Args:
            db_type: Database type
            connection_string: Database connection string
            **kwargs: Additional connection parameters

        Returns:
            Database connection instance
        """
        pass
