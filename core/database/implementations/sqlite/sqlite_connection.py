"""SQLite database connection implementation."""

import sqlite3
from pathlib import Path
from types import TracebackType
from typing import Any

from core.database.interfaces import DatabaseConnection, DatabaseTransaction
from core.log import get_logger
from core.types import DatabaseParamType

logger = get_logger(__name__)


class SQLiteConnection(DatabaseConnection):
    """SQLite database connection implementation."""

    def __init__(self, db_path: Path) -> None:
        """Initialize SQLite connection.

        Args:
            db_path: Path to SQLite database file
        """
        self.db_path = db_path
        self._connection: sqlite3.Connection | None = None

    async def connect(self) -> None:
        """Establish SQLite database connection."""
        try:
            self.db_path.parent.mkdir(parents=True, exist_ok=True)
            self._connection = sqlite3.connect(
                self.db_path,
                check_same_thread=False,
                timeout=60.0,
            )
            self._connection.row_factory = sqlite3.Row
            self._configure_connection()
            logger.info(f"Connected to SQLite: {self.db_path}")
        except sqlite3.Error as e:
            logger.error(f"Failed to connect to SQLite database: {e}")
            raise

    async def disconnect(self) -> None:
        """Close SQLite database connection."""
        if self._connection:
            self._connection.close()
            self._connection = None
            logger.info("Disconnected from SQLite")

    async def execute(self, query: str, params: DatabaseParamType = None) -> Any:
        """Execute a query.

        Args:
            query: SQL query
            params: Query parameters

        Returns:
            Query result
        """
        if not self._connection:
            raise RuntimeError("Database not connected")

        try:
            cursor = self._connection.cursor()
            if params:
                cursor.execute(query, params)
            else:
                cursor.execute(query)
            self._connection.commit()
            return cursor
        except sqlite3.Error as e:
            logger.error(f"Query execution failed: {e}")
            self._connection.rollback()
            raise

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
        if not self._connection:
            raise RuntimeError("Database not connected")

        try:
            cursor = self._connection.cursor()
            if params:
                cursor.execute(query, params)
            else:
                cursor.execute(query)
            row = cursor.fetchone()
            if row:
                return dict(row)
            return None
        except sqlite3.Error as e:
            logger.error(f"Fetch one failed: {e}")
            raise

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
        if not self._connection:
            raise RuntimeError("Database not connected")

        try:
            cursor = self._connection.cursor()
            if params:
                cursor.execute(query, params)
            else:
                cursor.execute(query)
            rows = cursor.fetchall()
            return [dict(row) for row in rows]
        except sqlite3.Error as e:
            logger.error(f"Fetch all failed: {e}")
            raise

    async def begin_transaction(self) -> DatabaseTransaction:
        """Begin a database transaction.

        Returns:
            Database transaction instance
        """
        if not self._connection:
            raise RuntimeError("Database not connected")
        return SQLiteTransaction(self._connection)

    @property
    def is_connected(self) -> bool:
        """Check if database is connected."""
        return self._connection is not None

    def _configure_connection(self) -> None:
        """Configure SQLite connection settings."""
        if not self._connection:
            return

        # For testing, use DELETE mode instead of WAL to avoid corruption issues
        self._connection.execute("PRAGMA journal_mode = DELETE")
        # Optimize for performance
        self._connection.execute("PRAGMA synchronous = NORMAL")
        # Enable foreign keys
        self._connection.execute("PRAGMA foreign_keys = ON")
        # Set busy timeout for better handling of concurrent access
        self._connection.execute("PRAGMA busy_timeout = 90000")
        # Set cache size for better performance
        self._connection.execute("PRAGMA cache_size = -64000")  # 64MB cache

    async def __aenter__(self) -> "SQLiteConnection":
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


class SQLiteTransaction(DatabaseTransaction):
    """SQLite database transaction implementation."""

    def __init__(self, connection: sqlite3.Connection) -> None:
        """Initialize SQLite transaction.

        Args:
            connection: SQLite connection
        """
        self._connection = connection

    async def commit(self) -> None:
        """Commit the transaction."""
        self._connection.commit()

    async def rollback(self) -> None:
        """Rollback the transaction."""
        self._connection.rollback()

    async def __aenter__(self) -> "SQLiteTransaction":
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
