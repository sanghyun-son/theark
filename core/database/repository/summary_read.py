"""Summary read repository using SQLModel with dependency injection."""

from datetime import UTC, datetime

from sqlmodel import Session, select

from core.database.repository.base import BaseRepository
from core.log import get_logger
from core.models.rows import SummaryRead

logger = get_logger(__name__)


class SummaryReadRepository(BaseRepository[SummaryRead]):
    """Summary read repository using SQLModel with dependency injection."""

    def __init__(self, db: Session) -> None:
        """Initialize summary read repository."""
        super().__init__(SummaryRead, db)

    def mark_as_read(self, user_id: int, summary_id: int) -> bool:
        """Mark a summary as read for a user."""
        # Check if already marked as read
        logger.debug(f"Marking summary {summary_id} as read for user {user_id}")
        statement = select(SummaryRead).where(
            SummaryRead.user_id == user_id,
            SummaryRead.summary_id == summary_id,
        )
        result = self.db.exec(statement)
        existing = result.first()
        if existing:
            logger.debug("Already marked as read, skipping insert")
            return True  # Already marked as read

        # Create new read record
        read_record = SummaryRead(
            user_id=user_id,
            summary_id=summary_id,
            read_at=datetime.now(UTC).isoformat(),
        )
        try:
            self.create(read_record)
            return True
        except Exception:
            return False

    def is_read_by_user(self, user_id: int, summary_id: int) -> bool:
        """Check if a summary is read by a user."""
        statement = select(SummaryRead).where(
            SummaryRead.user_id == user_id, SummaryRead.summary_id == summary_id
        )
        result = self.db.exec(statement)
        return result.first() is not None

    def is_summary_read_by_user(self, user_id: int, summary_id: int) -> bool:
        """Check if a summary is read by a user (alias for is_read_by_user)."""
        return self.is_read_by_user(user_id, summary_id)

    def get_read_summaries_for_user(self, user_id: int) -> list[SummaryRead]:
        """Get all summaries read by a user."""
        statement = select(SummaryRead).where(SummaryRead.user_id == user_id)
        result = self.db.exec(statement)
        return list(result.all())

    def get_read_summary_ids(self, user_id: int, summary_ids: list[int]) -> list[int]:
        """Get list of summary IDs that are read by user (batch operation).

        Args:
            user_id: User ID
            summary_ids: List of summary IDs to check

        Returns:
            List of summary IDs that are read by the user
        """
        if not summary_ids:
            return []

        statement = select(SummaryRead.summary_id).where(
            (SummaryRead.user_id == user_id) & (SummaryRead.summary_id.in_(summary_ids))
        )
        result = self.db.exec(statement)
        return list(result.all())
