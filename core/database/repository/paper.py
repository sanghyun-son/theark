"""Repository for paper operations."""

from core.database.interfaces import DatabaseManager
from core.models.database.entities import PaperEntity
from core.types import RepositoryRowType


class PaperRepository:
    """Repository for paper operations."""

    def __init__(self, db_manager: DatabaseManager) -> None:
        """Initialize repository with database manager."""
        self.db = db_manager

    def _row_to_paper(self, row: RepositoryRowType) -> PaperEntity:
        """Convert database row to Paper model.

        Args:
            row: Database row tuple or dict

        Returns:
            Paper model instance
        """
        if isinstance(row, dict):
            return PaperEntity.model_validate(row)

        return PaperEntity.from_tuple(row)

    async def create(self, paper: PaperEntity) -> int:
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

        cursor = await self.db.execute(query, params)
        return cursor.lastrowid  # type: ignore

    async def get_by_arxiv_id(self, arxiv_id: str) -> PaperEntity | None:
        """Get paper by arXiv ID.

        Args:
            arxiv_id: arXiv identifier

        Returns:
            Paper model or None if not found
        """
        query = "SELECT * FROM paper WHERE arxiv_id = ?"
        row = await self.db.fetch_one(query, (arxiv_id,))

        if row:
            return self._row_to_paper(row)
        return None

    async def get_by_id(self, paper_id: int) -> PaperEntity | None:
        """Get paper by ID.

        Args:
            paper_id: Paper ID

        Returns:
            Paper model or None if not found
        """
        query = "SELECT * FROM paper WHERE paper_id = ?"
        row = await self.db.fetch_one(query, (paper_id,))

        if row:
            return self._row_to_paper(row)
        return None

    async def update(self, paper: PaperEntity) -> bool:
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

        cursor = await self.db.execute(query, params)
        return bool(cursor.rowcount > 0)

    async def delete(self, paper_id: int) -> bool:
        """Delete a paper by ID.

        Args:
            paper_id: Paper ID to delete

        Returns:
            True if deleted, False if not found
        """
        query = "DELETE FROM paper WHERE paper_id = ?"
        cursor = await self.db.execute(query, (paper_id,))
        return bool(cursor.rowcount > 0)

    async def search_by_keywords(
        self, keywords: str, limit: int = 50
    ) -> list[PaperEntity]:
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
        rows = await self.db.fetch_all(query, (search_pattern, search_pattern, limit))
        papers = []

        for row in rows:
            papers.append(self._row_to_paper(row))

        return papers

    async def get_recent_papers(self, limit: int = 100) -> list[PaperEntity]:
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

        rows = await self.db.fetch_all(query, (limit,))
        papers = []

        for row in rows:
            papers.append(self._row_to_paper(row))

        return papers

    async def get_papers_paginated(
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
        count_row = await self.db.fetch_one(count_query, ())
        if count_row is None:
            total_count = 0
        else:
            total_count = count_row["COUNT(*)"]

        # Get papers with pagination
        query = """
        SELECT * FROM paper
        ORDER BY paper_id DESC
        LIMIT ? OFFSET ?
        """

        rows = await self.db.fetch_all(query, (limit, offset))
        papers = []

        for row in rows:
            papers.append(self._row_to_paper(row))

        return papers, total_count
