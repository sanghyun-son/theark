"""Repository for LLM request tracking."""

from typing import Any

from core import get_logger
from core.database import DatabaseManager
from core.models import LLMRequest, LLMUsageStats

logger = get_logger(__name__)


class LLMRequestRepository:
    """Repository for managing LLM request records."""

    def __init__(self, db_manager: DatabaseManager):
        """Initialize repository with database manager."""
        self.db_manager = db_manager

    def create_table(self) -> None:
        """Create the LLM requests table."""
        create_sql = """
        CREATE TABLE IF NOT EXISTS llm_requests (
            request_id INTEGER PRIMARY KEY AUTOINCREMENT,
            timestamp TEXT NOT NULL,
            model TEXT NOT NULL,
            provider TEXT NOT NULL DEFAULT 'openai',
            endpoint TEXT NOT NULL DEFAULT '/v1/chat/completions',
            is_batched BOOLEAN NOT NULL DEFAULT 0,
            request_type TEXT NOT NULL DEFAULT 'chat',
            custom_id TEXT,
            prompt_tokens INTEGER,
            completion_tokens INTEGER,
            total_tokens INTEGER,
            response_time_ms INTEGER,
            status TEXT NOT NULL DEFAULT 'pending',
            error_message TEXT,
            http_status_code INTEGER,
            estimated_cost_usd REAL,
            metadata TEXT,
            created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
        )
        """

        self.db_manager.execute(create_sql)

        # Create indexes for better performance
        self.db_manager.execute(
            "CREATE INDEX IF NOT EXISTS idx_llm_timestamp ON llm_requests(timestamp)"
        )
        self.db_manager.execute(
            "CREATE INDEX IF NOT EXISTS idx_llm_model ON llm_requests(model)"
        )
        self.db_manager.execute(
            "CREATE INDEX IF NOT EXISTS idx_llm_status ON llm_requests(status)"
        )
        self.db_manager.execute(
            "CREATE INDEX IF NOT EXISTS idx_llm_custom_id ON llm_requests(custom_id)"
        )

    def create(self, request: LLMRequest) -> int:
        """Create a new LLM request record."""
        insert_sql = """
        INSERT INTO llm_requests (
            timestamp, model, provider, endpoint,
            is_batched, request_type, custom_id,
            prompt_tokens, completion_tokens, total_tokens,
            response_time_ms, status, error_message, http_status_code,
            estimated_cost_usd, metadata
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """

        metadata_json = None
        if request.metadata:
            import json

            metadata_json = json.dumps(request.metadata)

        cursor = self.db_manager.execute(
            insert_sql,
            (
                request.timestamp,
                request.model,
                request.provider,
                request.endpoint,
                request.is_batched,
                request.request_type,
                request.custom_id,
                request.prompt_tokens,
                request.completion_tokens,
                request.total_tokens,
                request.response_time_ms,
                request.status,
                request.error_message,
                request.http_status_code,
                request.estimated_cost_usd,
                metadata_json,
            ),
        )
        return cursor.lastrowid or 0

    def update_status(
        self,
        request_id: int,
        status: str,
        response_time_ms: int | None = None,
        tokens: dict[str, int] | None = None,
        error_message: str | None = None,
        http_status_code: int | None = None,
        estimated_cost_usd: float | None = None,
    ) -> None:
        """Update request status and metrics."""
        update_parts: list[str] = ["status = ?"]
        params: list[Any] = [status]

        if response_time_ms is not None:
            update_parts.append("response_time_ms = ?")
            params.append(response_time_ms)

        if tokens:
            if "prompt_tokens" in tokens:
                update_parts.append("prompt_tokens = ?")
                params.append(tokens["prompt_tokens"])
            if "completion_tokens" in tokens:
                update_parts.append("completion_tokens = ?")
                params.append(tokens["completion_tokens"])
            if "total_tokens" in tokens:
                update_parts.append("total_tokens = ?")
                params.append(tokens["total_tokens"])

        if error_message is not None:
            update_parts.append("error_message = ?")
            params.append(error_message)

        if http_status_code is not None:
            update_parts.append("http_status_code = ?")
            params.append(http_status_code)

        if estimated_cost_usd is not None:
            update_parts.append("estimated_cost_usd = ?")
            params.append(estimated_cost_usd)

        update_sql = (
            f"UPDATE llm_requests SET {', '.join(update_parts)} WHERE request_id = ?"
        )
        params.append(request_id)

        self.db_manager.execute(update_sql, tuple(params))

    def get_by_id(self, request_id: int) -> LLMRequest | None:
        """Get LLM request by ID."""
        select_sql = """
        SELECT * FROM llm_requests WHERE request_id = ?
        """

        row = self.db_manager.fetch_one(select_sql, (request_id,))

        if row:
            return self._row_to_model(row)
        return None

    def get_by_custom_id(self, custom_id: str) -> list[LLMRequest]:
        """Get LLM requests by custom ID."""
        select_sql = """
        SELECT * FROM llm_requests WHERE custom_id = ?
        ORDER BY timestamp DESC
        """

        rows = self.db_manager.fetch_all(select_sql, (custom_id,))

        return [self._row_to_model(row) for row in rows]

    def get_recent(self, limit: int = 100) -> list[LLMRequest]:
        """Get recent LLM requests."""
        select_sql = """
        SELECT * FROM llm_requests
        ORDER BY timestamp DESC
        LIMIT ?
        """

        rows = self.db_manager.fetch_all(select_sql, (limit,))

        return [self._row_to_model(row) for row in rows]

    def get_usage_stats(
        self, start_date: str | None = None, end_date: str | None = None
    ) -> LLMUsageStats:
        """Get usage statistics for a date range."""
        where_clause = ""
        params = []

        if start_date:
            where_clause += " AND timestamp >= ?"
            params.append(start_date)
        if end_date:
            where_clause += " AND timestamp <= ?"
            params.append(end_date)

        stats_sql = f"""
        SELECT
            COUNT(*) as total_requests,
            SUM(CASE WHEN status = 'success' THEN 1 ELSE 0 END) as successful_requests,
            SUM(CASE WHEN status = 'error' THEN 1 ELSE 0 END) as failed_requests,
            SUM(COALESCE(total_tokens, 0)) as total_tokens,
            SUM(COALESCE(estimated_cost_usd, 0)) as total_cost_usd,
            AVG(COALESCE(response_time_ms, 0)) as avg_response_time_ms
        FROM llm_requests
        WHERE 1=1 {where_clause}
        """

        model_sql = f"""
        SELECT model, COUNT(*) as count
        FROM llm_requests
        WHERE 1=1 {where_clause}
        GROUP BY model
        ORDER BY count DESC
        LIMIT 1
        """

        # Get basic stats
        stats_row = self.db_manager.fetch_one(stats_sql, tuple(params))

        # Get most used model
        model_row = self.db_manager.fetch_one(model_sql, tuple(params))

        return LLMUsageStats(
            total_requests=stats_row[0] if stats_row else 0,
            successful_requests=stats_row[1] if stats_row else 0,
            failed_requests=stats_row[2] if stats_row else 0,
            total_tokens=stats_row[3] if stats_row else 0,
            total_cost_usd=stats_row[4] if stats_row else 0.0,
            average_response_time_ms=stats_row[5] if stats_row else 0.0,
            most_used_model=model_row[0] if model_row else None,
            date_range_start=start_date,
            date_range_end=end_date,
        )

    def _row_to_model(self, row: tuple[Any, ...]) -> LLMRequest:
        """Convert database row to LLMRequest model."""
        metadata = None
        if row[16]:  # metadata column index
            import json

            metadata = json.loads(row[16])

        return LLMRequest(
            request_id=row[0],  # request_id
            timestamp=row[1],  # timestamp
            model=row[2],  # model
            provider=row[3],  # provider
            endpoint=row[4],  # endpoint
            is_batched=bool(row[5]),  # is_batched
            request_type=row[6],  # request_type
            custom_id=row[7],  # custom_id
            prompt_tokens=row[8],  # prompt_tokens
            completion_tokens=row[9],  # completion_tokens
            total_tokens=row[10],  # total_tokens
            response_time_ms=row[11],  # response_time_ms
            status=row[12],  # status
            error_message=row[13],  # error_message
            http_status_code=row[14],  # http_status_code
            estimated_cost_usd=row[15],  # estimated_cost_usd
            metadata=metadata,
        )
