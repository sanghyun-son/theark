"""Batch state management for background processing."""

from typing import Any

from sqlalchemy.engine import Engine
from sqlmodel import Session

from core.database.repository.llm_batch import LLMBatchRepository
from core.log import get_logger
from core.models.batch import BatchItemCreate
from core.models.rows import Paper

logger = get_logger(__name__)


class BatchStateManager:
    """Manages batch request states and database interactions."""

    def __init__(self) -> None:
        """Initialize batch state manager."""
        # Note: db_session is injected per method call for flexibility

    def get_pending_summaries(self, db_engine: Engine) -> list[Paper]:
        """Get papers that need summarization.

        Args:
            db_engine: Database engine instance

        Returns:
            List of papers that need summarization
        """
        with Session(db_engine) as session:
            repository = LLMBatchRepository(session)

        return repository.get_pending_summaries()

    def get_active_batches(self, db_engine: Engine) -> list[dict[str, Any]]:
        """Get currently active batch requests.

        Args:
            db_engine: Database engine instance

        Returns:
            List of active batch requests
        """
        with Session(db_engine) as session:
            repository = LLMBatchRepository(session)

        return repository.get_active_batches()

    def create_batch_record(
        self,
        db_engine: Engine,
        batch_id: str,
        input_file_id: str,
        completion_window: str = "24h",
        endpoint: str = "/v1/chat/completions",
        metadata: dict[str, Any] | None = None,
    ) -> None:
        """Create a new batch request record.

        Args:
            db_engine: Database engine instance
            batch_id: Unique batch identifier
            input_file_id: ID of the input file
            completion_window: Time window for completion
            endpoint: API endpoint
            metadata: Additional metadata
        """
        with Session(db_engine) as session:
            repository = LLMBatchRepository(session)

        repository.create_batch_record(
            batch_id,
            input_file_id,
            completion_window,
            endpoint,
            metadata,
        )

    def update_batch_status(
        self,
        db_engine: Engine,
        batch_id: str,
        status: str,
        error_file_id: str | None = None,
    ) -> None:
        """Update batch request status.

        Args:
            db_engine: Database engine instance
            batch_id: Unique batch identifier
            status: New status
            error_file_id: ID of the error file (optional)
        """
        with Session(db_engine) as session:
            repository = LLMBatchRepository(session)

        repository.update_batch_status(batch_id, status, error_file_id)

    def add_batch_items(
        self, db_engine: Engine, batch_id: str, items: list[BatchItemCreate]
    ) -> None:
        """Add items to a batch request.

        Args:
            db_engine: Database engine instance
            batch_id: Unique batch identifier
            items: List of items to add
        """
        with Session(db_engine) as session:
            repository = LLMBatchRepository(session)

        items_dict = [item.model_dump() for item in items]
        repository.add_batch_items(batch_id, items_dict)

    def get_batch_items(self, db_engine: Engine, batch_id: str) -> list[dict[str, Any]]:
        """Get all items for a batch request.

        Args:
            db_engine: Database engine instance
            batch_id: Unique batch identifier

        Returns:
            List of batch items
        """
        with Session(db_engine) as session:
            repository = LLMBatchRepository(session)

        result = repository.get_batch_items(batch_id)
        return result if result else []

    def update_batch_item_status(
        self,
        db_engine: Engine,
        batch_id: str,
        paper_id: int,
        status: str,
        error_message: str | None = None,
    ) -> None:
        """Update status of a specific batch item.

        Args:
            db_engine: Database engine instance
            batch_id: Unique batch identifier
            paper_id: Paper identifier
            status: New status
            error_message: Error message if failed (optional)
        """
        with Session(db_engine) as session:
            repository = LLMBatchRepository(session)

        item_id = f"{batch_id}_{paper_id}"
        repository.update_batch_item_status(batch_id, item_id, status, error_message)

    def mark_papers_processing(self, db_engine: Engine, paper_ids: list[int]) -> None:
        """Mark papers as being processed.

        Args:
            db_session: Database session instance
            paper_ids: List of paper IDs to mark as processing
        """
        with Session(db_engine) as session:
            repository = LLMBatchRepository(session)

        repository.mark_papers_processing(paper_ids)
