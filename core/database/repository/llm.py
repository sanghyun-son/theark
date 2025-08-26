"""Repository for LLM request tracking."""

from typing import Any

from core.database.interfaces import DatabaseManager
from core.models import LLMRequest, LLMUsageStats
from core.types import RepositoryRowType


class LLMRequestRepository:
    """Repository for managing LLM request records."""

    def __init__(self, db_manager: DatabaseManager) -> None:
        """Initialize repository with database manager."""
        self.db = db_manager

    async def create(self, request: LLMRequest) -> int:
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

        cursor = await self.db.execute(
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

    async def update_status(
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

        await self.db.execute(update_sql, tuple(params))

    async def get_by_id(self, request_id: int) -> LLMRequest | None:
        """Get LLM request by ID."""
        select_sql = """
        SELECT * FROM llm_requests WHERE request_id = ?
        """

        row = await self.db.fetch_one(select_sql, (request_id,))

        if row:
            return self._row_to_llm_request(row)
        return None

    async def get_by_custom_id(self, custom_id: str) -> list[LLMRequest]:
        """Get LLM requests by custom ID."""
        select_sql = """
        SELECT * FROM llm_requests WHERE custom_id = ?
        ORDER BY timestamp DESC
        """

        rows = await self.db.fetch_all(select_sql, (custom_id,))

        return [self._row_to_llm_request(row) for row in rows]

    async def get_recent(self, limit: int = 100) -> list[LLMRequest]:
        """Get recent LLM requests."""
        select_sql = """
        SELECT * FROM llm_requests
        ORDER BY timestamp DESC
        LIMIT ?
        """

        rows = await self.db.fetch_all(select_sql, (limit,))

        return [self._row_to_llm_request(row) for row in rows]

    async def get_usage_stats(
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
        stats_row = await self.db.fetch_one(stats_sql, tuple(params))

        # Get most used model
        model_row = await self.db.fetch_one(model_sql, tuple(params))

        return LLMUsageStats(
            total_requests=stats_row["total_requests"] if stats_row else 0,
            successful_requests=stats_row["successful_requests"] if stats_row else 0,
            failed_requests=stats_row["failed_requests"] if stats_row else 0,
            total_tokens=stats_row["total_tokens"] if stats_row else 0,
            total_cost_usd=stats_row["total_cost_usd"] if stats_row else 0.0,
            average_response_time_ms=(
                stats_row["avg_response_time_ms"] if stats_row else 0.0
            ),
            most_used_model=model_row["model"] if model_row else None,
            date_range_start=start_date,
            date_range_end=end_date,
        )

    def _row_to_llm_request(self, row: RepositoryRowType) -> LLMRequest:
        """Convert database row to LLMRequest model.

        Args:
            row: Database row tuple or dict

        Returns:
            LLMRequest model instance
        """
        if isinstance(row, dict):
            return LLMRequest.model_validate(row)

        return LLMRequest.from_tuple(row)
