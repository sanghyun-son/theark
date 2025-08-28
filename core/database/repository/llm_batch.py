"""Repository for LLM batch operations."""

from typing import Any

from core.database.interfaces import DatabaseManager
from core.log import get_logger

logger = get_logger(__name__)


class LLMBatchRepository:
    """Repository for LLM batch operations."""

    def __init__(self, db_manager: DatabaseManager) -> None:
        """Initialize repository with database manager."""
        self._db_manager = db_manager

    async def get_pending_summaries(self) -> list[dict[str, Any]]:
        """Get papers that need summarization."""
        query = """
        SELECT p.* FROM paper p
        WHERE p.summary_status = 'batched'
        AND p.abstract IS NOT NULL
        AND p.abstract != ''
        ORDER BY p.published_at DESC
        LIMIT 1000
        """

        papers = await self._db_manager.fetch_all(query)
        logger.debug(f"Found {len(papers)} papers pending summarization")
        return papers

    async def update_paper_summary_status(self, paper_id: int, status: str) -> None:
        """Update the summary status of a paper.

        Args:
            paper_id: Paper ID to update
            status: New status ('batched', 'processing', 'done')
        """
        query = """
        UPDATE paper
        SET summary_status = ?
        WHERE paper_id = ?
        """

        await self._db_manager.execute(query, (status, paper_id))
        logger.debug(f"Updated paper {paper_id} summary status to {status}")

    async def mark_papers_processing(self, paper_ids: list[int]) -> None:
        """Mark papers as being processed.

        Args:
            paper_ids: List of paper IDs to mark as processing
        """
        if not paper_ids:
            return

        placeholders = ",".join(["?" for _ in paper_ids])
        query = f"""
        UPDATE paper
        SET summary_status = 'processing'
        WHERE paper_id IN ({placeholders})
        """

        await self._db_manager.execute(query, paper_ids)
        logger.debug(f"Marked {len(paper_ids)} papers as processing")

    async def get_active_batches(self) -> list[dict[str, Any]]:
        """Get currently active batch requests."""
        query = """
        SELECT * FROM llm_batch_requests
        WHERE status IN ('validating', 'in_progress', 'finalizing')
        ORDER BY created_at DESC
        """

        batches = await self._db_manager.fetch_all(query)
        logger.debug(f"Found {len(batches)} active batch requests")
        return batches

    async def create_batch_record(
        self,
        batch_id: str,
        input_file_id: str,
        completion_window: str = "24h",
        endpoint: str = "/v1/chat/completions",
        metadata: dict[str, Any] | None = None,
    ) -> None:
        """Create a new batch request record."""
        query = """
        INSERT INTO llm_batch_requests (
            batch_id, input_file_id, completion_window, endpoint, metadata
        ) VALUES (?, ?, ?, ?, ?)
        """

        metadata_json = None
        if metadata:
            import json

            metadata_json = json.dumps(metadata)

        await self._db_manager.execute(
            query,
            (batch_id, input_file_id, completion_window, endpoint, metadata_json),
        )
        logger.debug(f"Created batch record: {batch_id}")

    async def update_batch_status(
        self,
        batch_id: str,
        status: str,
        output_file_id: str | None = None,
        error_file_id: str | None = None,
        request_counts: dict[str, int] | None = None,
    ) -> None:
        """Update batch request status.

        Args:
            batch_id: Unique batch identifier
            status: New status
            output_file_id: ID of the output file (optional)
            error_file_id: ID of the error file (optional)
            request_counts: Counts of requests by status (optional)
        """
        # Build dynamic update query
        update_fields = ["status = ?"]
        params = [status]

        if output_file_id is not None:
            update_fields.append("output_file_id = ?")
            params.append(output_file_id)

        if error_file_id is not None:
            update_fields.append("error_file_id = ?")
            params.append(error_file_id)

        if request_counts is not None:
            import json

            update_fields.append("request_counts = ?")
            params.append(json.dumps(request_counts))

        # Add timestamp fields based on status
        if status == "in_progress":
            update_fields.append("in_progress_at = CURRENT_TIMESTAMP")
        elif status == "finalizing":
            update_fields.append("finalizing_at = CURRENT_TIMESTAMP")
        elif status in ["completed", "failed", "expired"]:
            update_fields.append("completed_at = CURRENT_TIMESTAMP")

        query = f"""
        UPDATE llm_batch_requests
        SET {', '.join(update_fields)}
        WHERE batch_id = ?
        """
        params.append(batch_id)

        await self._db_manager.execute(query, tuple(params))
        logger.debug(f"Updated batch {batch_id} status to {status}")

    async def add_batch_items(self, batch_id: str, items: list[dict[str, Any]]) -> None:
        """Add items to a batch request.

        Args:
            batch_id: Unique batch identifier
            items: List of items to add, each containing paper_id and input_data
        """
        if not items:
            logger.warning(f"No items to add to batch {batch_id}")
            return

        # Prepare batch insert
        query = """
        INSERT OR REPLACE INTO llm_batch_items (
            batch_id, paper_id, input_data
        ) VALUES (?, ?, ?)
        """

        # Execute batch insert
        for item in items:
            paper_id = item["paper_id"]
            input_data = item["input_data"]

            await self._db_manager.execute(query, (batch_id, paper_id, input_data))

        logger.debug(f"Added {len(items)} items to batch {batch_id}")

    async def get_batch_items(self, batch_id: str) -> list[dict[str, Any]]:
        """Get all items for a batch request.

        Args:
            batch_id: Unique batch identifier

        Returns:
            List of batch items
        """
        query = """
        SELECT * FROM llm_batch_items
        WHERE batch_id = ?
        ORDER BY created_at ASC
        """

        items = await self._db_manager.fetch_all(query, (batch_id,))
        logger.debug(f"Found {len(items)} items for batch {batch_id}")
        return items

    async def update_batch_item_status(
        self,
        batch_id: str,
        paper_id: int,
        status: str,
        output_data: str | None = None,
        error_message: str | None = None,
    ) -> None:
        """Update status of a specific batch item.

        Args:
            batch_id: Unique batch identifier
            paper_id: Paper identifier
            status: New status
            output_data: Output data from processing (optional)
            error_message: Error message if failed (optional)
        """
        # Build dynamic update query
        update_fields = ["status = ?"]
        params = [status]

        if output_data is not None:
            update_fields.append("output_data = ?")
            params.append(output_data)

        if error_message is not None:
            update_fields.append("error_message = ?")
            params.append(error_message)

        # Add processed_at timestamp for completed/failed items
        if status in ["completed", "failed"]:
            update_fields.append("processed_at = CURRENT_TIMESTAMP")

        query = f"""
        UPDATE llm_batch_items
        SET {', '.join(update_fields)}
        WHERE batch_id = ? AND paper_id = ?
        """
        params.append(batch_id)
        params.append(str(paper_id))

        await self._db_manager.execute(query, tuple(params))
        logger.debug(f"Updated batch item {batch_id}:{paper_id} status to {status}")
