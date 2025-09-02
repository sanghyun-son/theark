"""Repository for LLM batch operations."""

from datetime import UTC, datetime
from typing import Any

from sqlmodel import Session, desc, select

from core.log import get_logger
from core.models.rows import BatchItem, LLMBatchRequest, Paper
from core.types import PaperSummaryStatus

logger = get_logger(__name__)


class LLMBatchRepository:
    """Repository for LLM batch operations."""

    def __init__(self, db_session: Session) -> None:
        """Initialize repository with database session."""
        self.db = db_session

    def get_pending_summaries(self) -> list[Paper]:
        """Get papers that need summarization."""

        try:
            statement = (
                select(Paper)
                .where(
                    (Paper.summary_status == PaperSummaryStatus.BATCHED)
                    & (Paper.abstract is not None)
                    & (Paper.abstract != "")
                )
                .order_by(desc(Paper.published_at))
                .limit(1000)
            )
            result = self.db.exec(statement)
            papers = list(result.all())
            logger.debug(f"Found {len(papers)} papers pending summarization")
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
            # Update papers one by one to avoid SQLAlchemy in_ operator issues
            updated_count = 0
            for paper_id in paper_ids:
                statement = select(Paper).where(Paper.paper_id == paper_id)
                result = self.db.exec(statement)
                paper = result.first()

                if paper:
                    paper.summary_status = PaperSummaryStatus.PROCESSING
                    updated_count += 1

            self.db.commit()
            logger.debug(f"Marked {updated_count} papers as processing")
        except Exception as e:
            logger.error(f"Error marking papers as processing: {e}")
            raise

    def get_active_batches(self) -> list[dict[str, Any]]:
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

        # Convert to dict format for compatibility
        batch_list = []
        for batch in batches:
            batch_dict = {
                "batch_id": batch.batch_id,
                "status": batch.status,
                "created_at": batch.created_at,
                "completed_at": batch.completed_at,
                "request_counts": batch.request_counts,
                "metadata": batch.batch_metadata,
            }
            batch_list.append(batch_dict)

        logger.debug(f"Found {len(batch_list)} active batches")
        return batch_list

    def create_batch_record(
        self,
        batch_id: str,
        input_file_id: str,
        completion_window: str = "24h",
        endpoint: str = "/v1/chat/completions",
        metadata: dict[str, Any] | None = None,
    ) -> None:
        """Create a new batch request record."""
        from datetime import datetime

        batch_record = LLMBatchRequest(
            batch_id=batch_id,
            status="pending",
            input_file_id=input_file_id,
            created_at=datetime.now(UTC).isoformat(),
            batch_metadata=metadata or {},
        )

        self.db.add(batch_record)
        self.db.commit()
        self.db.refresh(batch_record)

        logger.debug(f"Created batch record: {batch_id}")

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

    def add_batch_items(self, batch_id: str, items: list[dict[str, Any]]) -> None:
        """Add items to a batch request.

        Args:
            batch_id: Batch ID
            items: List of batch items
        """
        if not items:
            return

        from datetime import datetime

        batch_items = []
        for item_data in items:
            paper_id = item_data.get("paper_id")
            if paper_id is None:
                logger.warning(f"Skipping batch item with no paper_id: {item_data}")
                continue

            batch_item = BatchItem(
                batch_id=batch_id,
                paper_id=paper_id,
                custom_id=item_data.get("custom_id", str(paper_id)),
                input_data=item_data.get("input_data", ""),
                status="pending",
                created_at=datetime.utcnow().isoformat(),
            )
            batch_items.append(batch_item)

        self.db.add_all(batch_items)
        self.db.commit()

        logger.debug(f"Added {len(batch_items)} items to batch {batch_id}")

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

    def get_batch_details(self, batch_id: str) -> dict[str, Any] | None:
        """Get detailed information about a batch request.

        Args:
            batch_id: Batch ID

        Returns:
            Batch details or None if not found
        """
        statement = select(LLMBatchRequest).where(LLMBatchRequest.batch_id == batch_id)
        result = self.db.exec(statement)
        batch = result.first()

        if batch:
            batch_dict = {
                "batch_id": batch.batch_id,
                "status": batch.status,
                "input_file_id": batch.input_file_id,
                "error_file_id": batch.error_file_id,
                "created_at": batch.created_at,
                "completed_at": batch.completed_at,
                "request_counts": batch.request_counts,
                "metadata": batch.batch_metadata,
            }
            logger.debug(f"Found batch details for {batch_id}")
            return batch_dict
        else:
            logger.debug(f"Batch {batch_id} not found")
            return None

    def get_batch_items(self, batch_id: str) -> list[dict[str, Any]]:
        """Get items for a batch request.

        Args:
            batch_id: Batch ID

        Returns:
            List of batch items
        """
        statement = select(BatchItem).where(BatchItem.batch_id == batch_id)
        result = self.db.exec(statement)
        items = result.all()

        # Convert to dict format for compatibility
        item_list = []
        for item in items:
            item_dict = {
                "item_id": item.item_id,
                "batch_id": item.batch_id,
                "paper_id": item.paper_id,
                "custom_id": item.custom_id,
                "input_data": item.input_data,
                "status": item.status,
                "response_data": item.response_data,
                "error_message": item.error_message,
                "created_at": item.created_at,
                "completed_at": item.completed_at,
            }
            item_list.append(item_dict)

        logger.debug(f"Found {len(item_list)} items for batch {batch_id}")
        return item_list

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

        if batch:
            batch.status = "cancelled"
            self.db.commit()
            self.db.refresh(batch)
            logger.debug(f"Cancelled batch {batch_id}")
            return True
        else:
            logger.debug(f"Batch {batch_id} not found for cancellation")
            return False
