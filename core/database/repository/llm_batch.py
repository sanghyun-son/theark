"""Repository for LLM batch operations."""

from datetime import UTC, datetime

from sqlalchemy import func
from sqlmodel import Session, desc, select

from core.log import get_logger
from core.models.batch import BatchInfo
from core.models.rows import LLMBatchRequest, Paper
from core.types import PaperSummaryStatus

logger = get_logger(__name__)


class LLMBatchRepository:
    """Repository for LLM batch operations."""

    def __init__(self, db_session: Session) -> None:
        """Initialize repository with database session."""
        self.db = db_session

    def get_pending_summaries(self, limit: int = 1000) -> list[Paper]:
        """Get papers that need summarization.

        Args:
            limit: Maximum number of papers to return (default: 1000)
        """

        try:
            statement = (
                select(Paper)
                .where(
                    (Paper.summary_status == PaperSummaryStatus.BATCHED)
                    & (Paper.abstract is not None)
                    & (Paper.abstract != "")
                )
                .order_by(desc(Paper.published_at))
                .limit(limit)
            )
            result = self.db.exec(statement)
            papers = list(result.all())
            logger.debug(
                f"Found {len(papers)} papers pending summarization (limit: {limit})"
            )
            return papers
        except Exception as exc:
            logger.error(f"Error getting pending summaries: {exc}")
            return []

    def update_paper_summary_status(
        self, paper_id: int, status: PaperSummaryStatus
    ) -> None:
        """Update the summary status of a paper.

        Args:
            paper_id: Paper ID to update
            status: New status
        """
        try:
            statement = select(Paper).where(Paper.paper_id == paper_id)
            result = self.db.exec(statement)
            paper = result.first()

            if paper:
                paper.summary_status = status
                self.db.commit()
                self.db.refresh(paper)
                logger.debug(f"Updated paper {paper_id} summary status to {status}")
            else:
                logger.warning(f"Paper {paper_id} not found for status update")
        except Exception as e:
            logger.error(f"Error updating paper {paper_id} status to {status}: {e}")
            raise

    def mark_papers_processing(self, paper_ids: list[int]) -> None:
        """Mark papers as being processed.

        Args:
            paper_ids: List of paper IDs to mark as processing
        """
        if not paper_ids:
            return

        try:
            # Use bulk update for better performance
            from core.database.repository.paper import PaperRepository

            paper_repo = PaperRepository(self.db)
            updated_count = paper_repo.update_summary_status_bulk(
                paper_ids, PaperSummaryStatus.PROCESSING
            )
            logger.debug(f"Marked {updated_count} papers as processing")
        except Exception as e:
            logger.error(f"Error marking papers as processing: {e}")
            # Just ignore failures as requested
            pass

    def get_active_batches(self) -> list[BatchInfo]:
        """Get currently active batch requests."""
        try:
            statement = select(LLMBatchRequest).where(
                LLMBatchRequest.status == "pending"
            )
            result = self.db.exec(statement)
            batches = result.all()
        except Exception as exc:
            logger.error(f"Error getting active batches: {exc}")
            return []

        # Convert to BatchInfo objects
        batch_list = []
        for batch in batches:
            batch_info = BatchInfo(
                batch_id=batch.batch_id,
                status=batch.status,
                created_at=batch.created_at,
                completed_at=batch.completed_at,
                entity_count=batch.entity_count,
                input_file_id=batch.input_file_id,
                error_file_id=batch.error_file_id,
            )
            batch_list.append(batch_info)

        logger.debug(f"Found {len(batch_list)} active batches")
        return batch_list

    def create_batch_record(
        self,
        batch_id: str,
        input_file_id: str,
        entity_count: int,
        completion_window: str = "24h",
        endpoint: str = "/v1/chat/completions",
    ) -> None:
        """Create a new batch request record."""
        from datetime import datetime

        batch_record = LLMBatchRequest(
            batch_id=batch_id,
            status="pending",
            input_file_id=input_file_id,
            entity_count=entity_count,
            created_at=datetime.now(UTC).isoformat(),
        )

        self.db.add(batch_record)
        self.db.commit()
        self.db.refresh(batch_record)

        logger.debug(f"Created batch record: {batch_id} with {entity_count} entities")

    def update_batch_status(
        self,
        batch_id: str,
        status: str,
        error_file_id: str | None = None,
    ) -> None:
        """Update batch request status.

        Args:
            batch_id: Batch ID to update
            status: New status
            error_file_id: Optional error file ID
        """

        statement = select(LLMBatchRequest).where(LLMBatchRequest.batch_id == batch_id)
        result = self.db.exec(statement)
        batch = result.first()

        if batch:
            batch.status = status
            if status in ["completed", "failed"]:
                batch.completed_at = datetime.now(UTC).isoformat()
            if error_file_id:
                batch.error_file_id = error_file_id

            self.db.commit()
            self.db.refresh(batch)
            logger.debug(f"Updated batch {batch_id} status to {status}")
        else:
            logger.warning(f"Batch {batch_id} not found for status update")

    def update_batch_status_with_metrics(
        self, batch_id: str, status: str, successful_count: int, failed_count: int
    ) -> None:
        """Update batch status and metrics in database.

        Args:
            batch_id: Batch ID
            status: New status
            successful_count: Number of successfully processed results
            failed_count: Number of failed results
        """
        batch = self.db.exec(
            select(LLMBatchRequest).where(LLMBatchRequest.batch_id == batch_id)
        ).first()

        if batch is None:
            logger.warning(f"Batch {batch_id} not found")
            return

        batch.status = status
        batch.successful_count = successful_count
        batch.failed_count = failed_count

        if status in ["completed", "failed"]:
            batch.completed_at = datetime.now(UTC).isoformat()

        self.db.commit()
        self.db.refresh(batch)
        logger.debug(
            f"Updated batch {batch_id} status to {status} with metrics: "
            f"{successful_count} successful, {failed_count} failed"
        )

    def update_batch_item_status(
        self, batch_id: str, item_id: str, status: str, error: str | None = None
    ) -> None:
        """Update batch item status.

        Args:
            batch_id: Batch ID
            item_id: Item ID
            status: New status
            error: Optional error message
        """
        # This would need to be implemented with a proper BatchItem model
        logger.debug(
            f"Updated batch item {item_id} in batch {batch_id} to status {status}"
        )
        if error:
            logger.debug(f"Error for item {item_id}: {error}")

    def get_batch_details(self, batch_id: str) -> BatchInfo | None:
        """Get detailed information about a batch request.

        Args:
            batch_id: Batch ID

        Returns:
            Batch details or None if not found
        """
        statement = select(LLMBatchRequest).where(LLMBatchRequest.batch_id == batch_id)
        result = self.db.exec(statement)
        batch = result.first()

        if batch is None:
            logger.warning(f"Batch {batch_id} not found")
            return None

        batch_info = BatchInfo(
            batch_id=batch.batch_id,
            status=batch.status,
            input_file_id=batch.input_file_id,
            error_file_id=batch.error_file_id,
            created_at=batch.created_at,
            completed_at=batch.completed_at,
            entity_count=batch.entity_count,
        )
        logger.debug(f"Found batch details for {batch_id}")
        return batch_info

    def cancel_batch(self, batch_id: str) -> bool:
        """Cancel a batch request.

        Args:
            batch_id: Batch ID to cancel

        Returns:
            True if cancelled, False if not found
        """
        statement = select(LLMBatchRequest).where(LLMBatchRequest.batch_id == batch_id)
        result = self.db.exec(statement)
        batch = result.first()

        if batch is None:
            logger.warning(f"Batch {batch_id} not found")
            return False

        batch.status = "cancelled"
        self.db.commit()
        self.db.refresh(batch)
        logger.debug(f"Cancelled batch {batch_id}")
        return True

    def check_daily_batch_limit(self, daily_limit: int) -> bool:
        """Check if daily batch limit has been reached.

        Args:
            daily_limit: Maximum number of batch requests allowed per day

        Returns:
            True if under daily limit, False otherwise
        """
        try:
            # Get today's date in UTC
            today = datetime.now(UTC).date()

            # Sum total entities from batch requests created today
            stmt = (
                select(func.sum(LLMBatchRequest.entity_count))
                .select_from(LLMBatchRequest)
                .where(func.date(LLMBatchRequest.created_at) == today)
            )
            result = self.db.exec(stmt).one()
            daily_count = result if result is not None else 0

            if daily_count >= daily_limit:
                logger.warning(f"Daily limit reached: {daily_count}/{daily_limit}")
                return False

            logger.debug(f"Daily batches: {daily_count}/{daily_limit}")
            return True

        except Exception as e:
            logger.error(f"Error checking daily batch limit: {e}")
            # On error, be conservative and return False
            return False
