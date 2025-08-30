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
