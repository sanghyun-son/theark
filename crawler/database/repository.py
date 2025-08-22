"""Repository layer for database operations."""

from .base import DatabaseManager
from .models import (
    AppUser,
    CrawlEvent,
    FeedItem,
    Paper,
    Summary,
    UserInterest,
    UserStar,
)


class PaperRepository:
    """Repository for paper operations."""

    def __init__(self, db_manager: DatabaseManager) -> None:
        """Initialize repository with database manager."""
        self.db = db_manager

    def _row_to_paper(self, row: tuple) -> Paper:
        """Convert database row to Paper model.

        Args:
            row: Database row tuple

        Returns:
            Paper model instance
        """
        return Paper(
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

    def create(self, paper: Paper) -> int:
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
        return cursor.lastrowid

    def get_by_arxiv_id(self, arxiv_id: str) -> Paper | None:
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

    def update(self, paper: Paper) -> bool:
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
        return cursor.rowcount > 0

    def search_by_keywords(self, keywords: str, limit: int = 50) -> list[Paper]:
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

    def get_recent_papers(self, limit: int = 100) -> list[Paper]:
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


class SummaryRepository:
    """Repository for summary operations."""

    def __init__(self, db_manager: DatabaseManager) -> None:
        """Initialize repository with database manager."""
        self.db = db_manager

    def _row_to_summary(self, row: tuple) -> Summary:
        """Convert database row to Summary model.

        Args:
            row: Database row tuple

        Returns:
            Summary model instance
        """
        return Summary(
            summary_id=row[0],
            paper_id=row[1],
            version=row[2],
            style=row[3],
            content=row[4],
            model=row[5],
            created_at=row[6],
        )

    def create(self, summary: Summary) -> int:
        """Create a new summary record.

        Args:
            summary: Summary model instance

        Returns:
            Created summary ID
        """
        query = """
        INSERT INTO summary (paper_id, version, style, content, model)
        VALUES (?, ?, ?, ?, ?)
        """
        params = (
            summary.paper_id,
            summary.version,
            summary.style,
            summary.content,
            summary.model,
        )

        cursor = self.db.execute(query, params)
        return cursor.lastrowid

    def get_by_paper_and_style(
        self, paper_id: int, style: str
    ) -> Summary | None:
        """Get summary by paper ID and style.

        Args:
            paper_id: Paper ID
            style: Summary style

        Returns:
            Summary model or None if not found
        """
        query = """
        SELECT * FROM summary 
        WHERE paper_id = ? AND style = ?
        ORDER BY version DESC
        LIMIT 1
        """

        row = self.db.fetch_one(query, (paper_id, style))

        if row:
            return self._row_to_summary(row)
        return None


class UserRepository:
    """Repository for user operations."""

    def __init__(self, db_manager: DatabaseManager) -> None:
        """Initialize repository with database manager."""
        self.db = db_manager

    def _row_to_user(self, row: tuple) -> AppUser:
        """Convert database row to AppUser model.

        Args:
            row: Database row tuple

        Returns:
            AppUser model instance
        """
        return AppUser(
            user_id=row[0],
            email=row[1],
            display_name=row[2],
        )

    def _row_to_interest(self, row: tuple) -> UserInterest:
        """Convert database row to UserInterest model.

        Args:
            row: Database row tuple

        Returns:
            UserInterest model instance
        """
        return UserInterest(
            user_id=row[0],
            kind=row[1],
            value=row[2],
            weight=row[3],
        )

    def _row_to_star(self, row: tuple) -> UserStar:
        """Convert database row to UserStar model.

        Args:
            row: Database row tuple

        Returns:
            UserStar model instance
        """
        return UserStar(
            user_id=row[0],
            paper_id=row[1],
            note=row[2],
            created_at=row[3],
        )

    def create_user(self, user: AppUser) -> int:
        """Create a new user.

        Args:
            user: User model instance

        Returns:
            Created user ID
        """
        query = "INSERT INTO app_user (email, display_name) VALUES (?, ?)"
        params = (user.email, user.display_name)

        cursor = self.db.execute(query, params)
        return cursor.lastrowid

    def get_user_by_email(self, email: str) -> AppUser | None:
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

    def add_interest(self, interest: UserInterest) -> None:
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

    def get_user_interests(self, user_id: int) -> list[UserInterest]:
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

    def add_star(self, star: UserStar) -> None:
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

    def get_user_stars(self, user_id: int, limit: int = 100) -> list[UserStar]:
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

    def _row_to_feed_item(self, row: tuple) -> FeedItem:
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
        return cursor.lastrowid

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

    def _row_to_crawl_event(self, row: tuple) -> CrawlEvent:
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
        return cursor.lastrowid

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
