"""Repository layer for database operations."""

from typing import Any

from core.database import DatabaseManager
from core.models import (
    CrawlEvent,
    FeedItem,
    PaperEntity,
    SummaryEntity,
    UserEntity,
    UserInterestEntity,
    UserStarEntity,
)


class PaperRepository:
    """Repository for paper operations."""

    def __init__(self, db_manager: DatabaseManager) -> None:
        """Initialize repository with database manager."""
        self.db = db_manager

    def _row_to_paper(self, row: tuple[Any, ...]) -> PaperEntity:
        """Convert database row to Paper model.

        Args:
            row: Database row tuple

        Returns:
            Paper model instance
        """
        return PaperEntity(
            paper_id=row[0],
            arxiv_id=row[1],
            latest_version=row[2],
            title=row[3],
            abstract=row[4],
            primary_category=row[5],
            categories=row[6],
            authors=row[7],
            url_abs=row[8],
            url_pdf=row[9],
            published_at=row[10],
            updated_at=row[11],
        )

    def create(self, paper: PaperEntity) -> int:
        """Create a new paper record.

        Args:
            paper: Paper model instance

        Returns:
            Created paper ID
        """
        query = """
        INSERT INTO paper (
            arxiv_id, latest_version, title, abstract, primary_category,
            categories, authors, url_abs, url_pdf, published_at, updated_at
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """
        params = (
            paper.arxiv_id,
            paper.latest_version,
            paper.title,
            paper.abstract,
            paper.primary_category,
            paper.categories,
            paper.authors,
            paper.url_abs,
            paper.url_pdf,
            paper.published_at,
            paper.updated_at,
        )

        cursor = self.db.execute(query, params)
        return cursor.lastrowid  # type: ignore

    def get_by_arxiv_id(self, arxiv_id: str) -> PaperEntity | None:
        """Get paper by arXiv ID.

        Args:
            arxiv_id: arXiv identifier

        Returns:
            Paper model or None if not found
        """
        query = "SELECT * FROM paper WHERE arxiv_id = ?"
        row = self.db.fetch_one(query, (arxiv_id,))

        if row:
            return self._row_to_paper(row)
        return None

    def get_by_id(self, paper_id: int) -> PaperEntity | None:
        """Get paper by ID.

        Args:
            paper_id: Paper ID

        Returns:
            Paper model or None if not found
        """
        query = "SELECT * FROM paper WHERE paper_id = ?"
        row = self.db.fetch_one(query, (paper_id,))

        if row:
            return self._row_to_paper(row)
        return None

    def update(self, paper: PaperEntity) -> bool:
        """Update an existing paper.

        Args:
            paper: Paper model with paper_id

        Returns:
            True if updated, False if not found
        """
        if not paper.paper_id:
            raise ValueError("Paper ID is required for update")

        query = """
        UPDATE paper SET
            latest_version = ?, title = ?, abstract = ?, primary_category = ?,
            categories = ?, authors = ?, url_abs = ?, url_pdf = ?, updated_at = ?
        WHERE paper_id = ?
        """
        params = (
            paper.latest_version,
            paper.title,
            paper.abstract,
            paper.primary_category,
            paper.categories,
            paper.authors,
            paper.url_abs,
            paper.url_pdf,
            paper.updated_at,
            paper.paper_id,
        )

        cursor = self.db.execute(query, params)
        return bool(cursor.rowcount > 0)

    def delete(self, paper_id: int) -> bool:
        """Delete a paper by ID.

        Args:
            paper_id: Paper ID to delete

        Returns:
            True if deleted, False if not found
        """
        query = "DELETE FROM paper WHERE paper_id = ?"
        cursor = self.db.execute(query, (paper_id,))
        return bool(cursor.rowcount > 0)

    def search_by_keywords(self, keywords: str, limit: int = 50) -> list[PaperEntity]:
        """Search papers by keywords using simple LIKE search.

        Args:
            keywords: Search keywords
            limit: Maximum number of results

        Returns:
            List of matching papers
        """
        query = """
        SELECT * FROM paper
        WHERE title LIKE ? OR abstract LIKE ?
        ORDER BY published_at DESC
        LIMIT ?
        """

        search_pattern = f"%{keywords}%"
        rows = self.db.fetch_all(query, (search_pattern, search_pattern, limit))
        papers = []

        for row in rows:
            papers.append(self._row_to_paper(row))

        return papers

    def get_recent_papers(self, limit: int = 100) -> list[PaperEntity]:
        """Get recent papers ordered by publication date.

        Args:
            limit: Maximum number of results

        Returns:
            List of recent papers
        """
        query = """
        SELECT * FROM paper
        ORDER BY published_at DESC
        LIMIT ?
        """

        rows = self.db.fetch_all(query, (limit,))
        papers = []

        for row in rows:
            papers.append(self._row_to_paper(row))

        return papers

    def get_papers_paginated(
        self, limit: int = 20, offset: int = 0
    ) -> tuple[list[PaperEntity], int]:
        """Get papers with pagination, ordered by latest first.

        Args:
            limit: Number of papers to return
            offset: Number of papers to skip

        Returns:
            Tuple of (papers list, total count)
        """
        # Get total count
        count_query = "SELECT COUNT(*) FROM paper"
        count_row = self.db.fetch_one(count_query, ())
        if count_row is None:
            total_count = 0
        else:
            total_count = count_row[0]

        # Get papers with pagination
        query = """
        SELECT * FROM paper
        ORDER BY paper_id DESC
        LIMIT ? OFFSET ?
        """

        rows = self.db.fetch_all(query, (limit, offset))
        papers = []

        for row in rows:
            papers.append(self._row_to_paper(row))

        return papers, total_count


class SummaryRepository:
    """Repository for summary operations."""

    def __init__(self, db_manager: DatabaseManager) -> None:
        """Initialize repository with database manager."""
        from core import get_logger

        logger = get_logger(__name__)
        self.db = db_manager

        # Log the database manager state for debugging
        logger.debug(f"SummaryRepository initialized with db_manager: {db_manager}")
        if hasattr(db_manager, "connection"):
            logger.debug(f"Database connection state: {db_manager.connection}")

    def _row_to_summary(self, row: tuple[Any, ...]) -> SummaryEntity:
        """Convert database row to Summary model.

        Args:
            row: Database row tuple

        Returns:
            Summary model instance
        """
        return SummaryEntity(
            summary_id=row[0],
            paper_id=row[1],
            version=row[2],
            overview=row[3],
            motivation=row[4],
            method=row[5],
            result=row[6],
            conclusion=row[7],
            language=row[8],
            interests=row[9],
            relevance=row[10],
            model=row[11],
            is_read=bool(row[12]),
            created_at=row[13],
        )

    def create(self, summary: SummaryEntity) -> int:
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

        cursor = self.db.execute(query, params)
        return cursor.lastrowid  # type: ignore

    def get_by_paper_and_language(
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

        row = self.db.fetch_one(query, (paper_id, language))

        if row:
            return self._row_to_summary(row)
        return None

    def get_by_paper_id(self, paper_id: int) -> list[SummaryEntity]:
        """Get all summaries for a paper.

        Args:
            paper_id: Paper ID

        Returns:
            List of summaries for the paper
        """
        query = "SELECT * FROM summary WHERE paper_id = ? ORDER BY version DESC"
        rows = self.db.fetch_all(query, (paper_id,))
        summaries = []

        for row in rows:
            summaries.append(self._row_to_summary(row))

        return summaries

    def get_by_id(self, summary_id: int) -> SummaryEntity | None:
        """Get summary by ID.

        Args:
            summary_id: Summary ID

        Returns:
            Summary model or None if not found
        """
        query = "SELECT * FROM summary WHERE summary_id = ?"
        row = self.db.fetch_one(query, (summary_id,))

        if row:
            return self._row_to_summary(row)
        return None

    def update(self, summary: SummaryEntity) -> bool:
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

        cursor = self.db.execute(query, params)
        return bool(cursor.rowcount > 0)

    def delete(self, summary_id: int) -> bool:
        """Delete a summary by ID.

        Args:
            summary_id: Summary ID to delete

        Returns:
            True if deleted, False if not found
        """
        query = "DELETE FROM summary WHERE summary_id = ?"
        cursor = self.db.execute(query, (summary_id,))
        return bool(cursor.rowcount > 0)


class UserRepository:
    """Repository for user operations."""

    def __init__(self, db_manager: DatabaseManager) -> None:
        """Initialize repository with database manager."""
        self.db = db_manager

    def _row_to_user(self, row: tuple[Any, ...]) -> UserEntity:
        """Convert database row to AppUser model.

        Args:
            row: Database row tuple

        Returns:
            AppUser model instance
        """
        return UserEntity(
            user_id=row[0],
            email=row[1],
            display_name=row[2],
        )

    def _row_to_interest(self, row: tuple[Any, ...]) -> UserInterestEntity:
        """Convert database row to UserInterest model.

        Args:
            row: Database row tuple

        Returns:
            UserInterest model instance
        """
        return UserInterestEntity(
            user_id=row[0],
            kind=row[1],
            value=row[2],
            weight=row[3],
        )

    def _row_to_star(self, row: tuple[Any, ...]) -> UserStarEntity:
        """Convert database row to UserStar model.

        Args:
            row: Database row tuple

        Returns:
            UserStar model instance
        """
        return UserStarEntity(
            user_id=row[0],
            paper_id=row[1],
            note=row[2],
            created_at=row[3],
        )

    def create_user(self, user: UserEntity) -> int:
        """Create a new user.

        Args:
            user: User model instance

        Returns:
            Created user ID
        """
        query = "INSERT INTO app_user (email, display_name) VALUES (?, ?)"
        params = (user.email, user.display_name)

        cursor = self.db.execute(query, params)
        return cursor.lastrowid  # type: ignore

    def get_user_by_email(self, email: str) -> UserEntity | None:
        """Get user by email.

        Args:
            email: User email

        Returns:
            User model or None if not found
        """
        query = "SELECT * FROM app_user WHERE email = ?"
        row = self.db.fetch_one(query, (email,))

        if row:
            return self._row_to_user(row)
        return None

    def add_interest(self, interest: UserInterestEntity) -> None:
        """Add or update user interest.

        Args:
            interest: User interest model
        """
        query = """
        INSERT OR REPLACE INTO user_interest (user_id, kind, value, weight)
        VALUES (?, ?, ?, ?)
        """
        params = (
            interest.user_id,
            interest.kind,
            interest.value,
            interest.weight,
        )
        self.db.execute(query, params)

    def get_user_interests(self, user_id: int) -> list[UserInterestEntity]:
        """Get all interests for a user.

        Args:
            user_id: User ID

        Returns:
            List of user interests
        """
        query = "SELECT * FROM user_interest WHERE user_id = ?"
        rows = self.db.fetch_all(query, (user_id,))

        interests = []
        for row in rows:
            interests.append(self._row_to_interest(row))

        return interests

    def add_star(self, star: UserStarEntity) -> None:
        """Add a star/bookmark for a user.

        Args:
            star: User star model
        """
        query = """
        INSERT OR REPLACE INTO user_star (user_id, paper_id, note)
        VALUES (?, ?, ?)
        """
        params = (star.user_id, star.paper_id, star.note)
        self.db.execute(query, params)

    def remove_star(self, user_id: int, paper_id: int) -> bool:
        """Remove a star/bookmark for a user.

        Args:
            user_id: User ID
            paper_id: Paper ID

        Returns:
            True if removed, False if not found
        """
        query = "DELETE FROM user_star WHERE user_id = ? AND paper_id = ?"
        cursor = self.db.execute(query, (user_id, paper_id))
        return bool(cursor.rowcount > 0)

    def get_user_stars(self, user_id: int, limit: int = 100) -> list[UserStarEntity]:
        """Get all stars for a user.

        Args:
            user_id: User ID
            limit: Maximum number of results

        Returns:
            List of user stars
        """
        query = """
        SELECT * FROM user_star
        WHERE user_id = ?
        ORDER BY created_at DESC
        LIMIT ?
        """

        rows = self.db.fetch_all(query, (user_id, limit))
        stars = []

        for row in rows:
            stars.append(self._row_to_star(row))

        return stars


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


class CrawlEventRepository:
    """Repository for crawl event operations."""

    def __init__(self, db_manager: DatabaseManager) -> None:
        """Initialize repository with database manager."""
        self.db = db_manager

    def _row_to_crawl_event(self, row: tuple[Any, ...]) -> CrawlEvent:
        """Convert database row to CrawlEvent model.

        Args:
            row: Database row tuple

        Returns:
            CrawlEvent model instance
        """
        return CrawlEvent(
            event_id=row[0],
            arxiv_id=row[1],
            event_type=row[2],
            detail=row[3],
            created_at=row[4],
        )

    def log_event(self, event: CrawlEvent) -> int:
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

        cursor = self.db.execute(query, params)
        return cursor.lastrowid  # type: ignore

    def get_recent_events(self, limit: int = 100) -> list[CrawlEvent]:
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

        rows = self.db.fetch_all(query, (limit,))
        events = []

        for row in rows:
            events.append(self._row_to_crawl_event(row))

        return events
