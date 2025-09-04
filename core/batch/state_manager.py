"""Batch state management for background processing."""

from sqlalchemy.engine import Engine
from sqlmodel import Session

from core.database.repository.llm_batch import LLMBatchRepository
from core.log import get_logger
from core.models.batch import BatchInfo
from core.models.rows import Paper

logger = get_logger(__name__)


class BatchStateManager:
    """Manages batch request states and database interactions."""

    def __init__(self) -> None:
        """Initialize batch state manager."""
        # Note: db_session is injected per method call for flexibility

    def get_pending_summaries(
        self, db_engine: Engine, limit: int = 1000
    ) -> list[Paper]:
        """Get papers that need summarization.

        Args:
            db_engine: Database engine instance
            limit: Maximum number of papers to return (default: 1000)

        Returns:
            List of papers that need summarization
        """
        with Session(db_engine) as session:
            repository = LLMBatchRepository(session)

        return repository.get_pending_summaries(limit=limit)

    def get_active_batches(self, db_engine: Engine) -> list[BatchInfo]:
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
        entity_count: int,
        completion_window: str = "24h",
        endpoint: str = "/v1/chat/completions",
    ) -> None:
        """Create a new batch request record.

        Args:
            db_engine: Database engine instance
            batch_id: Unique batch identifier
            input_file_id: ID of the input file
            entity_count: Number of entities in this batch
            completion_window: Time window for completion
            endpoint: API endpoint
        """
        with Session(db_engine) as session:
            repository = LLMBatchRepository(session)

        repository.create_batch_record(
            batch_id,
            input_file_id,
            entity_count,
            completion_window,
            endpoint,
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

    def check_daily_batch_limit(self, db_engine: Engine, daily_limit: int) -> bool:
        """Check if daily batch limit has been reached.

        Args:
            db_engine: Database engine instance
            daily_limit: Maximum number of batch requests allowed per day

        Returns:
            True if under daily limit, False otherwise
        """
        with Session(db_engine) as session:
            repository = LLMBatchRepository(session)

        return repository.check_daily_batch_limit(daily_limit)

    def mark_papers_processing(self, db_engine: Engine, paper_ids: list[int]) -> None:
        """Mark papers as being processed.

        Args:
            db_session: Database session instance
            paper_ids: List of paper IDs to mark as processing
        """
        with Session(db_engine) as session:
            repository = LLMBatchRepository(session)

        repository.mark_papers_processing(paper_ids)
