"""SQLite database manager implementation using the new interface."""

from pathlib import Path
from typing import Any, Type, TypeVar

from core.database.interfaces import DatabaseManager
from core.database.interfaces.connection import DatabaseConnection
from core.database.interfaces.repository import Repository
from core.log import get_logger
from core.types import DatabaseParamType

from .query_builder import SQLiteQueryBuilder
from .sqlite_connection import SQLiteConnection

T = TypeVar("T")


logger = get_logger(__name__)


class SQLiteManager(DatabaseManager):
    """SQLite database manager implementation using the new interface."""

    def __init__(self, db_path: str | Path, **kwargs: Any) -> None:
        """Initialize SQLite manager.

        Args:
            db_path: Path to SQLite database file
            **kwargs: Additional configuration parameters
        """
        super().__init__(str(db_path), **kwargs)
        self.db_path = Path(db_path)
        self._connection = SQLiteConnection(self.db_path)
        self._query_builder = SQLiteQueryBuilder()

    async def connect(self) -> None:
        """Establish SQLite database connection."""
        try:
            self.db_path.parent.mkdir(parents=True, exist_ok=True)
            await self._connection.connect()
            logger.info(f"Connected to SQLiteManager: {self.db_path}")
        except Exception as e:
            logger.error(f"Failed to connect to SQLite database: {e}")
            raise

    async def disconnect(self) -> None:
        """Close SQLite database connection."""
        await self._connection.disconnect()
        logger.info("Disconnected from SQLiteManager")

    async def execute(
        self,
        query: str,
        params: DatabaseParamType = None,
    ) -> Any:
        """Execute a query.

        Args:
            query: SQL query
            params: Query parameters

        Returns:
            Query result
        """
        return await self._connection.execute(query, params)

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
            Single row as dictionary or None
        """
        return await self._connection.fetch_one(query, params)

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
        return await self._connection.fetch_all(query, params)

    def get_repository(self, entity_type: Type[Any]) -> Repository[Any]:
        """Get repository for entity type.

        Args:
            entity_type: Type of entity

        Returns:
            Repository instance
        """
        raise NotImplementedError("Repository factory pattern not implemented")

    @property
    def connection(self) -> DatabaseConnection:
        """Get database connection."""
        return self._connection

    @property
    def is_connected(self) -> bool:
        """Check if database is connected."""
        return self._connection.is_connected

    async def create_tables(self) -> None:
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
                paper_id      INTEGER NOT NULL
                              REFERENCES paper(paper_id)
                              ON DELETE CASCADE,
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
                is_read       BOOLEAN NOT NULL DEFAULT 0,
                created_at    TEXT NOT NULL DEFAULT (datetime('now')),
                UNIQUE (paper_id, version, language)
            )""",
            # 3) 사용자
            """CREATE TABLE IF NOT EXISTS app_user (
                user_id      INTEGER PRIMARY KEY AUTOINCREMENT,
                email        TEXT NOT NULL UNIQUE,
                display_name TEXT
            )""",
            # 4) 사용자 관심사
            """CREATE TABLE IF NOT EXISTS user_interest (
                user_id   INTEGER NOT NULL REFERENCES app_user(user_id)
                          ON DELETE CASCADE,
                kind      TEXT NOT NULL,
                value     TEXT NOT NULL,
                weight    REAL NOT NULL DEFAULT 1.0,
                PRIMARY KEY (user_id, kind, value)
            )""",
            # 5) 사용자 즐겨찾기
            """CREATE TABLE IF NOT EXISTS user_star (
                user_id     INTEGER NOT NULL REFERENCES app_user(user_id)
                            ON DELETE CASCADE,
                paper_id    INTEGER NOT NULL REFERENCES paper(paper_id)
                            ON DELETE CASCADE,
                note        TEXT,
                created_at  TEXT NOT NULL DEFAULT (datetime('now')),
                PRIMARY KEY (user_id, paper_id)
            )""",
            # 6) 피드 아이템
            """CREATE TABLE IF NOT EXISTS feed_item (
                feed_item_id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id      INTEGER NOT NULL REFERENCES app_user(user_id)
                             ON DELETE CASCADE,
                paper_id     INTEGER NOT NULL REFERENCES paper(paper_id)
                             ON DELETE CASCADE,
                score        REAL NOT NULL,
                feed_date    TEXT NOT NULL,
                created_at   TEXT NOT NULL DEFAULT (datetime('now')),
                UNIQUE (user_id, paper_id, feed_date)
            )""",
            # 7) 크롤 이벤트
            """CREATE TABLE IF NOT EXISTS crawl_event (
                event_id     INTEGER PRIMARY KEY AUTOINCREMENT,
                arxiv_id     TEXT,
                event_type   TEXT NOT NULL,
                detail       TEXT,
                created_at   TEXT NOT NULL DEFAULT (datetime('now'))
            )""",
            # 8) LLM 추적 테이블
            """CREATE TABLE IF NOT EXISTS llm_tracking (
                tracking_id INTEGER PRIMARY KEY AUTOINCREMENT,
                model_name TEXT NOT NULL,
                prompt_tokens INTEGER DEFAULT 0,
                completion_tokens INTEGER DEFAULT 0,
                total_tokens INTEGER DEFAULT 0,
                cost_usd REAL DEFAULT 0.0,
                request_time REAL,
                response_time REAL,
                success BOOLEAN DEFAULT 1,
                error_message TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )""",
            # 9) LLM 요청 테이블
            """CREATE TABLE IF NOT EXISTS llm_requests (
                request_id INTEGER PRIMARY KEY AUTOINCREMENT,
                timestamp TEXT NOT NULL,
                model TEXT NOT NULL,
                provider TEXT NOT NULL,
                endpoint TEXT NOT NULL,
                is_batched BOOLEAN NOT NULL DEFAULT 0,
                request_type TEXT NOT NULL,
                custom_id TEXT,
                status TEXT NOT NULL DEFAULT 'pending',
                metadata TEXT,
                prompt_tokens INTEGER DEFAULT 0,
                completion_tokens INTEGER DEFAULT 0,
                total_tokens INTEGER DEFAULT 0,
                response_time_ms INTEGER,
                error_message TEXT,
                http_status_code INTEGER,
                estimated_cost_usd REAL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )""",
            # 9) 인덱스들
            """CREATE INDEX IF NOT EXISTS idx_paper_published_at
                ON paper(published_at DESC)""",
            """CREATE INDEX IF NOT EXISTS idx_paper_primary_category
                ON paper(primary_category)""",
            """CREATE INDEX IF NOT EXISTS idx_user_star_user
                ON user_star(user_id, created_at DESC)""",
            """CREATE INDEX IF NOT EXISTS idx_summary_paper
                ON summary(paper_id, language)""",
            """CREATE INDEX IF NOT EXISTS idx_llm_tracking_model
                ON llm_tracking(model_name, created_at DESC)""",
            """CREATE INDEX IF NOT EXISTS idx_llm_timestamp
                ON llm_requests(timestamp)""",
            """CREATE INDEX IF NOT EXISTS idx_llm_model
                ON llm_requests(model)""",
            """CREATE INDEX IF NOT EXISTS idx_llm_status
                ON llm_requests(status)""",
            """CREATE INDEX IF NOT EXISTS idx_llm_custom_id
                ON llm_requests(custom_id)""",
        ]

        try:
            for statement in statements:
                await self._connection.execute(statement)
            logger.info("Database tables created successfully")
        except Exception as e:
            logger.error(f"Failed to create tables: {e}")
            raise

    async def drop_tables(self) -> None:
        """Drop all database tables."""

        tables = [
            "llm_tracking",
            "feed_item",
            "user_star",
            "user_interest",
            "app_user",
            "summary",
            "crawl_event",
            "paper",
        ]

        try:
            for table in tables:
                await self._connection.execute(f"DROP TABLE IF EXISTS {table}")
            logger.info("Database tables dropped successfully")
        except Exception as e:
            logger.error(f"Failed to drop tables: {e}")
            raise

    async def track_token_usage(
        self,
        model: str,
        prompt_tokens: int,
        completion_tokens: int,
        total_tokens: int,
        cost: float | None = None,
    ) -> None:
        """Track token usage for LLM models."""

        query = """
            INSERT INTO llm_tracking (
                model_name, prompt_tokens, completion_tokens,
                total_tokens, cost_usd, request_time, response_time, success
            ) VALUES (
                :model_name,
                :prompt_tokens,
                :completion_tokens,
                :total_tokens,
                :cost_usd,
                :request_time,
                :response_time,
                :success
            )
        """

        import time

        current_time = time.time()

        try:
            await self._connection.execute(
                query,
                {
                    "model_name": model,
                    "prompt_tokens": prompt_tokens,
                    "completion_tokens": completion_tokens,
                    "total_tokens": total_tokens,
                    "cost_usd": cost or 0.0,
                    "request_time": current_time,
                    "response_time": current_time,
                    "success": True,
                },
            )
            logger.debug(
                f"Tracked token usage for model {model}: {total_tokens} tokens"
            )
        except Exception as e:
            logger.error(f"Failed to track token usage: {e}")
            raise

    async def get_token_usage_stats(
        self,
        model: str | None = None,
        start_date: str | None = None,
        end_date: str | None = None,
    ) -> dict[str, Any]:
        """Get token usage statistics."""

        where_conditions = []
        params = {}

        if model:
            where_conditions.append("model_name = :model")
            params["model"] = model

        if start_date:
            where_conditions.append("created_at >= :start_date")
            params["start_date"] = start_date

        if end_date:
            where_conditions.append("created_at <= :end_date")
            params["end_date"] = end_date

        where_clause = " AND ".join(where_conditions) if where_conditions else "1=1"

        query = f"""
            SELECT
                model_name,
                COUNT(*) as request_count,
                SUM(prompt_tokens) as total_prompt_tokens,
                SUM(completion_tokens) as total_completion_tokens,
                SUM(total_tokens) as total_tokens,
                SUM(cost_usd) as total_cost,
                AVG(request_time) as avg_request_time
            FROM llm_tracking
            WHERE {where_clause}
            GROUP BY model_name
        """

        try:
            results = await self._connection.fetch_all(query, params)
            return {
                "stats": results,
                "filters": {
                    "model": model,
                    "start_date": start_date,
                    "end_date": end_date,
                },
            }
        except Exception as e:
            logger.error(f"Failed to get token usage stats: {e}")
            raise

    async def track_request_status(
        self,
        request_id: str,
        status: str,
        model: str | None = None,
        error_message: str | None = None,
    ) -> None:
        """Track LLM request status using query builder."""

        data = {
            "model_name": model or "unknown",
            "prompt_tokens": 0,
            "completion_tokens": 0,
            "total_tokens": 0,
            "cost_usd": 0.0,
            "success": 1 if status.lower() == "success" else 0,
            "error_message": error_message,
        }

        query, params = self._query_builder.insert("llm_tracking", data)
        await self._connection.execute(query, params)

    async def get_request_history(
        self, request_id: str | None = None, status: str | None = None, limit: int = 100
    ) -> list[dict[str, Any]]:
        """Get request history using query builder."""

        where_conditions: dict[str, Any] = {}
        if request_id:
            where_conditions["tracking_id"] = request_id
        if status:
            where_conditions["success"] = 1 if status.lower() == "success" else 0

        query, params = self._query_builder.select(
            "llm_tracking",
            columns=[
                "tracking_id as request_id",
                "model_name",
                "prompt_tokens",
                "completion_tokens",
                "total_tokens",
                "cost_usd",
                "request_time",
                "response_time",
                "success",
                "error_message",
                "created_at",
            ],
            where=where_conditions,
            order_by=["created_at DESC"],
            limit=limit,
        )

        results = await self._connection.fetch_all(query, params)
        return results
