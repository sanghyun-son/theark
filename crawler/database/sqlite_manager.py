"""SQLite database manager implementation."""

import sqlite3
from pathlib import Path
from typing import Any

from .base import DatabaseManager


class SQLiteManager(DatabaseManager):
    """SQLite database manager implementation."""

    def __init__(self, db_path: str | Path) -> None:
        """Initialize SQLite manager.

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
            self.logger.info(f"Connected to SQLite database: {self.db_path}")
        except sqlite3.Error as e:
            self.logger.error(f"Failed to connect to SQLite database: {e}")
            raise

    def disconnect(self) -> None:
        """Close SQLite database connection."""
        if self.connection:
            self.connection.close()
            self.connection = None
            self.logger.info("Disconnected from SQLite database")

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
        # Set busy timeout
        self.connection.execute("PRAGMA busy_timeout = 30000")

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
            self.logger.error(f"Query execution failed: {e}")
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
            self.logger.error(f"Batch query execution failed: {e}")
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
            self.logger.error(f"Fetch one failed: {e}")
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
            self.logger.error(f"Fetch all failed: {e}")
            raise

    def create_tables(self) -> None:
        """Create all necessary database tables."""
        # Define schema as individual statements
        statements = [
            # 1) 논문
            """CREATE TABLE IF NOT EXISTS paper (
                paper_id        INTEGER PRIMARY KEY AUTOINCREMENT,
                arxiv_id        TEXT NOT NULL UNIQUE,
                latest_version  INTEGER NOT NULL DEFAULT 1,
                title           TEXT NOT NULL,
                abstract        TEXT NOT NULL,
                primary_category TEXT NOT NULL,
                categories      TEXT NOT NULL,
                authors         TEXT NOT NULL,
                url_abs         TEXT NOT NULL,
                url_pdf         TEXT,
                published_at    TEXT NOT NULL,
                updated_at      TEXT NOT NULL
            )""",
            # 2) 요약
            """CREATE TABLE IF NOT EXISTS summary (
                summary_id    INTEGER PRIMARY KEY AUTOINCREMENT,
                paper_id      INTEGER NOT NULL REFERENCES paper(paper_id) ON DELETE CASCADE,
                version       INTEGER NOT NULL,
                overview      TEXT NOT NULL,
                motivation    TEXT NOT NULL,
                method        TEXT NOT NULL,
                result        TEXT NOT NULL,
                conclusion    TEXT NOT NULL,
                language      TEXT NOT NULL,
                interests     TEXT NOT NULL,
                relevance     INTEGER NOT NULL,
                model         TEXT,
                created_at    TEXT NOT NULL DEFAULT (datetime('now')),
                UNIQUE (paper_id, version, language)
            )""",  # noqa: E501
            # 3) 사용자
            """CREATE TABLE IF NOT EXISTS app_user (
                user_id      INTEGER PRIMARY KEY AUTOINCREMENT,
                email        TEXT NOT NULL UNIQUE,
                display_name TEXT
            )""",
            # 4) 사용자 관심사
            """CREATE TABLE IF NOT EXISTS user_interest (
                user_id   INTEGER NOT NULL REFERENCES app_user(user_id) ON DELETE CASCADE,
                kind      TEXT NOT NULL,
                value     TEXT NOT NULL,
                weight    REAL NOT NULL DEFAULT 1.0,
                PRIMARY KEY (user_id, kind, value)
            )""",  # noqa: E501
            # 5) 사용자 즐겨찾기
            """CREATE TABLE IF NOT EXISTS user_star (
                user_id     INTEGER NOT NULL REFERENCES app_user(user_id) ON DELETE CASCADE,
                paper_id    INTEGER NOT NULL REFERENCES paper(paper_id) ON DELETE CASCADE,
                note        TEXT,
                created_at  TEXT NOT NULL DEFAULT (datetime('now')),
                PRIMARY KEY (user_id, paper_id)
            )""",  # noqa: E501
            # 6) 피드 아이템
            """CREATE TABLE IF NOT EXISTS feed_item (
                feed_item_id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id      INTEGER NOT NULL REFERENCES app_user(user_id) ON DELETE CASCADE,
                paper_id     INTEGER NOT NULL REFERENCES paper(paper_id) ON DELETE CASCADE,
                score        REAL NOT NULL,
                feed_date    TEXT NOT NULL,
                created_at   TEXT NOT NULL DEFAULT (datetime('now')),
                UNIQUE (user_id, paper_id, feed_date)
            )""",  # noqa: E501
            # 7) 크롤 이벤트
            """CREATE TABLE IF NOT EXISTS crawl_event (
                event_id     INTEGER PRIMARY KEY AUTOINCREMENT,
                arxiv_id     TEXT,
                event_type   TEXT NOT NULL,
                detail       TEXT,
                created_at   TEXT NOT NULL DEFAULT (datetime('now'))
            )""",  # noqa: E501
            # 8) 인덱스들
            """CREATE INDEX IF NOT EXISTS idx_paper_published_at
                ON paper(published_at DESC)""",
            """CREATE INDEX IF NOT EXISTS idx_paper_primary_category
                ON paper(primary_category)""",
            """CREATE INDEX IF NOT EXISTS idx_user_star_user
                ON user_star(user_id, created_at DESC)""",
            """CREATE INDEX IF NOT EXISTS idx_summary_paper
                ON summary(paper_id, language)""",
        ]

        try:
            for statement in statements:
                self.execute(statement)

            self.logger.info("Database tables created successfully")
        except sqlite3.Error as e:
            self.logger.error(f"Failed to create tables: {e}")
            raise

    def __enter__(self) -> "SQLiteManager":
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
