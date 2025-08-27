"""Batch state management for background processing."""

from typing import Any

from core.database.interfaces import DatabaseManager
from core.database.repository.llm_batch import LLMBatchRepository
from core.log import get_logger

logger = get_logger(__name__)


class BatchStateManager:
    """Manages batch request states and database interactions."""

    def __init__(self) -> None:
        """Initialize batch state manager."""
        # Note: db_manager is injected per method call for flexibility

    async def get_pending_summaries(
        self, db_manager: DatabaseManager
    ) -> list[dict[str, Any]]:
        """Get papers that need summarization.

        Args:
            db_manager: Database manager instance

        Returns:
            List of papers that need summarization
        """
        repository = LLMBatchRepository(db_manager)
        return await repository.get_pending_summaries()

    async def get_active_batches(
        self, db_manager: DatabaseManager
    ) -> list[dict[str, Any]]:
        """Get currently active batch requests.

        Args:
            db_manager: Database manager instance

        Returns:
            List of active batch requests
        """
        repository = LLMBatchRepository(db_manager)
        return await repository.get_active_batches()

    async def create_batch_record(
        self,
        db_manager: DatabaseManager,
        batch_id: str,
        input_file_id: str,
        completion_window: str = "24h",
        endpoint: str = "/v1/chat/completions",
        metadata: dict[str, Any] | None = None,
    ) -> None:
        """Create a new batch request record.

        Args:
            db_manager: Database manager instance
            batch_id: Unique batch identifier
            input_file_id: ID of the input file
            completion_window: Time window for completion
            endpoint: API endpoint
            metadata: Additional metadata
        """
        repository = LLMBatchRepository(db_manager)
        await repository.create_batch_record(
            batch_id, input_file_id, completion_window, endpoint, metadata
        )

    async def update_batch_status(
        self,
        db_manager: DatabaseManager,
        batch_id: str,
        status: str,
        output_file_id: str | None = None,
        error_file_id: str | None = None,
        request_counts: dict[str, int] | None = None,
    ) -> None:
        """Update batch request status.

        Args:
            db_manager: Database manager instance
            batch_id: Unique batch identifier
            status: New status
            output_file_id: ID of the output file (optional)
            error_file_id: ID of the error file (optional)
            request_counts: Counts of requests by status (optional)
        """
        repository = LLMBatchRepository(db_manager)
        await repository.update_batch_status(
            batch_id, status, output_file_id, error_file_id, request_counts
        )

    async def add_batch_items(
        self, db_manager: DatabaseManager, batch_id: str, items: list[dict[str, Any]]
    ) -> None:
        """Add items to a batch request.

        Args:
            db_manager: Database manager instance
            batch_id: Unique batch identifier
            items: List of items to add, each containing paper_id and input_data
        """
        repository = LLMBatchRepository(db_manager)
        await repository.add_batch_items(batch_id, items)

    async def get_batch_items(
        self, db_manager: DatabaseManager, batch_id: str
    ) -> list[dict[str, Any]]:
        """Get all items for a batch request.

        Args:
            db_manager: Database manager instance
            batch_id: Unique batch identifier

        Returns:
            List of batch items
        """
        repository = LLMBatchRepository(db_manager)
        return await repository.get_batch_items(batch_id)

    async def update_batch_item_status(
        self,
        db_manager: DatabaseManager,
        batch_id: str,
        paper_id: int,
        status: str,
        output_data: str | None = None,
        error_message: str | None = None,
    ) -> None:
        """Update status of a specific batch item.

        Args:
            db_manager: Database manager instance
            batch_id: Unique batch identifier
            paper_id: Paper identifier
            status: New status
            output_data: Output data from processing (optional)
            error_message: Error message if failed (optional)
        """
        repository = LLMBatchRepository(db_manager)
        await repository.update_batch_item_status(
            batch_id, paper_id, status, output_data, error_message
        )
