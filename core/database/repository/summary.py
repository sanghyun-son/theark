"""Repository for summary operations."""

from core import get_logger
from core.database.interfaces import DatabaseManager
from core.models.database.entities import SummaryEntity
from core.types import RepositoryRowType

logger = get_logger(__name__)


class SummaryRepository:
    """Repository for summary operations."""

    def __init__(self, db_manager: DatabaseManager) -> None:
        """Initialize repository with database manager."""
        self.db = db_manager

    def _row_to_summary(self, row: RepositoryRowType) -> SummaryEntity:
        """Convert database row to Summary model.

        Args:
            row: Database row as dict or tuple

        Returns:
            Summary model instance
        """
        if isinstance(row, dict):
            return SummaryEntity.model_validate(row)

        return SummaryEntity.from_tuple(row)

    async def create(self, summary: SummaryEntity) -> int:
        """Create a new summary record.

        Args:
            summary: Summary model instance

        Returns:
            Created summary ID
        """
        query = """
        INSERT INTO summary (
            paper_id, version, overview, motivation, method, result,
            conclusion, language, interests, relevance, model, is_read
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """
        params = (
            summary.paper_id,
            summary.version,
            summary.overview,
            summary.motivation,
            summary.method,
            summary.result,
            summary.conclusion,
            summary.language,
            summary.interests,
            summary.relevance,
            summary.model,
            summary.is_read,
        )

        cursor = await self.db.execute(query, params)
        return cursor.lastrowid  # type: ignore

    async def get_by_paper_and_language(
        self, paper_id: int, language: str
    ) -> SummaryEntity | None:
        """Get summary by paper ID and language.

        Args:
            paper_id: Paper ID
            language: Summary language

        Returns:
            Summary model or None if not found
        """
        query = """
        SELECT * FROM summary
        WHERE paper_id = ? AND language = ?
        ORDER BY version DESC
        LIMIT 1
        """

        row = await self.db.fetch_one(query, (paper_id, language))

        if row:
            return self._row_to_summary(row)
        return None

    async def get_by_paper_id(self, paper_id: int) -> list[SummaryEntity]:
        """Get all summaries for a paper.

        Args:
            paper_id: Paper ID

        Returns:
            List of summaries for the paper
        """
        query = "SELECT * FROM summary WHERE paper_id = ? ORDER BY version DESC"
        rows = await self.db.fetch_all(query, (paper_id,))
        summaries = []

        for row in rows:
            summaries.append(self._row_to_summary(row))

        return summaries

    async def get_by_id(self, summary_id: int) -> SummaryEntity | None:
        """Get summary by ID.

        Args:
            summary_id: Summary ID

        Returns:
            Summary model or None if not found
        """
        query = "SELECT * FROM summary WHERE summary_id = ?"
        row = await self.db.fetch_one(query, (summary_id,))

        if row:
            return self._row_to_summary(row)
        return None

    async def update(self, summary: SummaryEntity) -> bool:
        """Update a summary.

        Args:
            summary: Summary model with updated data

        Returns:
            True if updated, False if not found
        """
        if not summary.summary_id:
            return False

        query = """
        UPDATE summary SET
            overview = ?, motivation = ?, method = ?, result = ?,
            conclusion = ?, language = ?, interests = ?, relevance = ?,
            model = ?, is_read = ?
        WHERE summary_id = ?
        """
        params = (
            summary.overview,
            summary.motivation,
            summary.method,
            summary.result,
            summary.conclusion,
            summary.language,
            summary.interests,
            summary.relevance,
            summary.model,
            summary.is_read,
            summary.summary_id,
        )

        cursor = await self.db.execute(query, params)
        return bool(cursor.rowcount > 0)

    async def delete(self, summary_id: int) -> bool:
        """Delete a summary by ID.

        Args:
            summary_id: Summary ID to delete

        Returns:
            True if deleted, False if not found
        """
        query = "DELETE FROM summary WHERE summary_id = ?"
        cursor = await self.db.execute(query, (summary_id,))
        return bool(cursor.rowcount > 0)
