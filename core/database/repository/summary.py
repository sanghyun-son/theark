"""Summary repository using SQLModel with dependency injection."""

from sqlmodel import Session, select

from core.database.repository.base import BaseRepository
from core.log import get_logger
from core.models.rows import Summary

logger = get_logger(__name__)


class SummaryRepository(BaseRepository[Summary]):
    """Summary repository using SQLModel with dependency injection."""

    def __init__(self, db: Session) -> None:
        """Initialize summary repository."""
        super().__init__(Summary, db)

    async def get_by_paper_id(self, paper_id: int) -> list[Summary]:
        """Get summaries by paper ID.

        Args:
            paper_id: Paper ID

        Returns:
            List of summaries for the paper
        """
        statement = select(Summary).where(Summary.paper_id == paper_id)
        result = self.db.exec(statement)
        return list(result.all())

    def get_by_paper_id_and_language(
        self, paper_id: int, language: str
    ) -> Summary | None:
        """Get summary by paper ID and language.

        Args:
            paper_id: Paper ID
            language: Summary language

        Returns:
            Summary if found, None otherwise
        """
        statement = select(Summary).where(
            (Summary.paper_id == paper_id) & (Summary.language == language)
        )
        result = self.db.exec(statement)
        return result.first()

    def get_by_paper_and_language(self, paper_id: int, language: str) -> Summary | None:
        """Get summary by paper ID and language (alias for compatibility).

        Args:
            paper_id: Paper ID
            language: Summary language

        Returns:
            Summary if found, None otherwise
        """
        return self.get_by_paper_id_and_language(paper_id, language)

    def mark_as_read(self, summary_id: int) -> bool:
        """Mark a summary as read.

        Args:
            summary_id: Summary ID

        Returns:
            True if updated, False if not found
        """
        statement = select(Summary).where(Summary.summary_id == summary_id)
        result = self.db.exec(statement)
        summary = result.first()

        if summary:
            summary.is_read = True
            self.db.commit()
            self.db.refresh(summary)
            return True

        return False
