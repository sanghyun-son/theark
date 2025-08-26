"""Repository for crawl event operations."""

from core.database.interfaces import DatabaseManager
from core.models import CrawlEvent
from core.types import RepositoryRowType


class CrawlEventRepository:
    """Repository for crawl event operations."""

    def __init__(self, db_manager: DatabaseManager) -> None:
        """Initialize repository with database manager."""
        self.db = db_manager

    def _row_to_crawl_event(self, row: RepositoryRowType) -> CrawlEvent:
        """Convert database row to CrawlEvent model.

        Args:
            row: Database row tuple or dict

        Returns:
            CrawlEvent model instance
        """
        if isinstance(row, dict):
            return CrawlEvent.model_validate(row)

        return CrawlEvent.from_tuple(row)

    async def log_event(self, event: CrawlEvent) -> int:
        """Log a crawl event.

        Args:
            event: Crawl event model

        Returns:
            Created event ID
        """
        query = """
        INSERT INTO crawl_event (arxiv_id, event_type, detail)
        VALUES (?, ?, ?)
        """
        params = (event.arxiv_id, event.event_type, event.detail)

        cursor = await self.db.execute(query, params)
        return cursor.lastrowid  # type: ignore

    async def get_recent_events(self, limit: int = 100) -> list[CrawlEvent]:
        """Get recent crawl events.

        Args:
            limit: Maximum number of results

        Returns:
            List of crawl events
        """
        query = """
        SELECT * FROM crawl_event
        ORDER BY created_at DESC
        LIMIT ?
        """

        rows = await self.db.fetch_all(query, (limit,))
        events = []

        for row in rows:
            events.append(self._row_to_crawl_event(row))

        return events
