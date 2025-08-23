"""Base SQLite manager with shared functionality."""

import sqlite3
from pathlib import Path
from typing import Any

from core.log import get_logger

from .base import DatabaseManager

logger = get_logger(__name__)


class BaseSQLiteManager(DatabaseManager):
    """Base SQLite manager with shared functionality."""

    def __init__(self, db_path: str | Path) -> None:
        """Initialize base SQLite manager.

        Args:
            db_path: Path to SQLite database file
        """
        super().__init__(str(db_path))
        self.db_path = Path(db_path)
        self.connection: sqlite3.Connection | None = None

    def connect(self) -> None:
        """Establish SQLite database connection."""
        try:
            self.db_path.parent.mkdir(parents=True, exist_ok=True)
            self.connection = sqlite3.connect(
                self.db_path,
                check_same_thread=False,
                timeout=30.0,
            )
            self.connection.row_factory = sqlite3.Row
            self._configure_connection()
            logger.info(f"Connected to SQLite database: {self.db_path}")
        except sqlite3.Error as e:
            logger.error(f"Failed to connect to SQLite database: {e}")
            raise

    def disconnect(self) -> None:
        """Close SQLite database connection."""
        if self.connection:
            self.connection.close()
            self.connection = None
            logger.info("Disconnected from SQLite database")

    def _configure_connection(self) -> None:
        """Configure SQLite connection settings."""
        if not self.connection:
            return

        # For testing, use DELETE mode instead of WAL to avoid corruption issues
        self.connection.execute("PRAGMA journal_mode = DELETE")
        # Optimize for performance
        self.connection.execute("PRAGMA synchronous = NORMAL")
        # Enable foreign keys
        self.connection.execute("PRAGMA foreign_keys = ON")
        # Set busy timeout for better handling of concurrent access
        self.connection.execute("PRAGMA busy_timeout = 60000")
        # Set WAL mode for better concurrent access (if not in testing)
        # self.connection.execute("PRAGMA journal_mode = WAL")
        # Set cache size for better performance
        self.connection.execute("PRAGMA cache_size = -64000")  # 64MB cache

    def execute(self, query: str, params: tuple[Any, ...] | None = None) -> Any:
        """Execute a database query.

        Args:
            query: SQL query string
            params: Query parameters

        Returns:
            Query result
        """
        if not self.connection:
            raise RuntimeError("Database not connected")

        try:
            cursor = self.connection.cursor()
            if params:
                cursor.execute(query, params)
            else:
                cursor.execute(query)
            self.connection.commit()
            return cursor
        except sqlite3.Error as e:
            logger.error(f"Query execution failed: {e}")
            self.connection.rollback()
            raise

    def execute_many(self, query: str, params_list: list[tuple[Any, ...]]) -> None:
        """Execute a query with multiple parameter sets.

        Args:
            query: SQL query string
            params_list: List of parameter tuples
        """
        if not self.connection:
            raise RuntimeError("Database not connected")

        try:
            cursor = self.connection.cursor()
            cursor.executemany(query, params_list)
            self.connection.commit()
        except sqlite3.Error as e:
            logger.error(f"Batch query execution failed: {e}")
            self.connection.rollback()
            raise

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
        if not self.connection:
            raise RuntimeError("Database not connected")

        try:
            cursor = self.connection.cursor()
            if params:
                cursor.execute(query, params)
            else:
                cursor.execute(query)
            return cursor.fetchone()  # type: ignore
        except sqlite3.Error as e:
            logger.error(f"Fetch one failed: {e}")
            raise

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
        if not self.connection:
            raise RuntimeError("Database not connected")

        try:
            cursor = self.connection.cursor()
            if params:
                cursor.execute(query, params)
            else:
                cursor.execute(query)
            return cursor.fetchall()
        except sqlite3.Error as e:
            logger.error(f"Fetch all failed: {e}")
            raise

    def __enter__(self) -> "BaseSQLiteManager":
        """Context manager entry."""
        self.connect()
        return self

    def __exit__(
        self,
        exc_type: type[BaseException] | None,
        exc_val: BaseException | None,
        exc_tb: Any,
    ) -> None:
        """Context manager exit."""
        self.disconnect()
