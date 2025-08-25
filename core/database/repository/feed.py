"""Repository for feed operations."""

from typing import Any

from core.database.base import DatabaseManager
from core.models import FeedItem


class FeedRepository:
    """Repository for feed operations."""

    def __init__(self, db_manager: DatabaseManager) -> None:
        """Initialize repository with database manager."""
        self.db = db_manager

    def _row_to_feed_item(self, row: tuple[Any, ...]) -> FeedItem:
        """Convert database row to FeedItem model.

        Args:
            row: Database row tuple

        Returns:
            FeedItem model instance
        """
        return FeedItem(
            feed_item_id=row[0],
            user_id=row[1],
            paper_id=row[2],
            score=row[3],
            feed_date=row[4],
            created_at=row[5],
        )

    def add_feed_item(self, feed_item: FeedItem) -> int:
        """Add a feed item.

        Args:
            feed_item: Feed item model

        Returns:
            Created feed item ID
        """
        query = """
        INSERT OR REPLACE INTO feed_item (user_id, paper_id, score, feed_date)
        VALUES (?, ?, ?, ?)
        """
        params = (
            feed_item.user_id,
            feed_item.paper_id,
            feed_item.score,
            feed_item.feed_date,
        )

        cursor = self.db.execute(query, params)
        return cursor.lastrowid  # type: ignore

    def get_user_feed(
        self, user_id: int, feed_date: str, limit: int = 50
    ) -> list[FeedItem]:
        """Get feed items for a user on a specific date.

        Args:
            user_id: User ID
            feed_date: Feed date (YYYY-MM-DD)
            limit: Maximum number of results

        Returns:
            List of feed items
        """
        query = """
        SELECT * FROM feed_item
        WHERE user_id = ? AND feed_date = ?
        ORDER BY score DESC
        LIMIT ?
        """

        rows = self.db.fetch_all(query, (user_id, feed_date, limit))
        feed_items = []

        for row in rows:
            feed_items.append(self._row_to_feed_item(row))

        return feed_items
