"""Core paper repository with CRUD operations."""

from __future__ import annotations

from typing import Any

from sqlmodel import Session, desc, select, update

from core.database.repository.base import BaseRepository
from core.log import get_logger
from core.models.rows import Paper, Summary, SummaryRead, UserStar
from core.models.types import ArxivID, PaperID
from core.types import PaperSummaryStatus

from .query_builders import PaperJoinQueryBuilder, PaperQueryBuilder

logger = get_logger(__name__)


class PaperRepository(BaseRepository[Paper]):
    """Repository for Paper model operations."""

    def __init__(self, db: Session) -> None:
        super().__init__(Paper, db)
        self.query_builder = PaperQueryBuilder(db)
        self.join_query_builder = PaperJoinQueryBuilder(db)

    def _get_paper_ids(self, papers: list[Paper]) -> list[int]:
        """Extract paper IDs from Paper objects."""
        return [paper.paper_id for paper in papers if paper.paper_id is not None]

    def _fetch_summaries_for_papers(
        self,
        papers: list[Paper],
        language: str = "Korean",
    ) -> dict[PaperID, Summary]:
        """Fetch summaries for a list of papers.

        Args:
            papers: List of Paper objects
            language: Language for summaries

        Returns:
            Dictionary mapping paper_id to Summary object
        """
        if not papers:
            return {}

        paper_ids = self._get_paper_ids(papers)
        statement = select(Summary).where(
            Summary.paper_id.in_(paper_ids),  # type: ignore[union-attr]
            Summary.language == language,
        )
        result = self.db.exec(statement)
        summaries = result.all()

        return {
            summary.paper_id: summary
            for summary in summaries
            if summary.paper_id is not None
        }

    def get_by_arxiv_id(self, arxiv_id: ArxivID) -> Paper | None:
        """Get paper by arXiv ID.

        Args:
            arxiv_id: arXiv ID to search for

        Returns:
            Paper object if found, None otherwise
        """
        statement = select(Paper).where(Paper.arxiv_id == arxiv_id)
        result = self.db.exec(statement)
        return result.first()

    def get_papers_with_summaries(
        self,
        skip: int = 0,
        limit: int = 100,
        language: str = "Korean",
        prioritize_summaries: bool = False,
        sort_by_relevance: bool = False,
        categories: list[str] | None = None,
    ) -> list[Paper]:
        """Get papers with their summaries using optimized query.

        Args:
            skip: Number of records to skip
            limit: Maximum number of records to return
            language: Language for summaries
            prioritize_summaries: Whether to prioritize papers with summaries
            sort_by_relevance: Whether to sort by relevance score
            categories: List of categories to filter by

        Returns:
            List of Paper objects
        """
        # Early exit: Combined priority and relevance
        if prioritize_summaries and sort_by_relevance:
            logger.debug(
                f"Using combined query: "
                f"prioritize_summaries={prioritize_summaries}, "
                f"sort_by_relevance={sort_by_relevance}"
            )
            query = self.query_builder.build_combined_query(
                skip=skip,
                limit=limit,
                categories=categories,
                language=language,
            )
            result = self.db.exec(query)
            query_results = result.all()
            return [row[0] for row in query_results]

        # Early exit: Priority only
        if prioritize_summaries:
            logger.debug(
                f"Using priority query: "
                f"prioritize_summaries={prioritize_summaries}, "
                f"skip={skip}, limit={limit}"
            )
            priority_query = self.query_builder.build_priority_query(
                skip=skip, limit=limit, categories=categories
            )
            priority_result = self.db.exec(priority_query)
            papers = list(priority_result.all())
            logger.debug(f"Priority query returned {len(papers)} papers")
            if papers:
                logger.debug(f"First paper summary_status: {papers[0].summary_status}")
            return papers

        # Early exit: Relevance only
        if sort_by_relevance:
            relevance_query = self.query_builder.build_relevance_query(
                skip=skip,
                limit=limit,
                categories=categories,
                language=language,
            )
            relevance_result = self.db.exec(relevance_query)
            query_results = relevance_result.all()
            return [row[0] for row in query_results]

        # Default: Simple query
        simple_query = self.query_builder.build_simple_query(
            skip=skip, limit=limit, categories=categories
        )
        simple_result = self.db.exec(simple_query)
        return list(simple_result.all())

    def get_papers_with_overview_optimized(
        self,
        skip: int = 0,
        limit: int = 100,
        language: str = "Korean",
        prioritize_summaries: bool = False,
        sort_by_relevance: bool = False,
        categories: list[str] | None = None,
    ) -> list[Paper]:
        """Get papers with overview using optimized query.

        Args:
            skip: Number of records to skip
            limit: Maximum number of records to return
            language: Language for summaries
            prioritize_summaries: Whether to prioritize papers with summaries
            sort_by_relevance: Whether to sort by relevance score
            categories: List of categories to filter by

        Returns:
            List of Paper objects
        """
        return self.get_papers_with_summaries(
            skip=skip,
            limit=limit,
            language=language,
            prioritize_summaries=prioritize_summaries,
            sort_by_relevance=sort_by_relevance,
            categories=categories,
        )

    def get_papers_with_summaries_join(
        self,
        skip: int = 0,
        limit: int = 100,
        language: str = "Korean",
    ) -> list[tuple[Paper, Summary]]:
        """Get papers with summaries using JOIN approach.

        Args:
            skip: Number of records to skip
            limit: Maximum number of records to return
            language: Language for summaries

        Returns:
            List of PaperListItemResponse with papers and their summaries
        """
        statement = self.join_query_builder.build_papers_with_summaries_join(
            skip=skip, limit=limit, language=language
        )

        result = self.db.exec(statement)
        rows = list(result.all())

        papers_with_summaries = []
        for row in rows:
            paper, summary = row
            papers_with_summaries.append((paper, summary))

        return papers_with_summaries

    def get_papers_with_user_status_join(
        self,
        skip: int = 0,
        limit: int = 100,
        language: str = "Korean",
    ) -> list[tuple[Paper, Summary, UserStar, SummaryRead]]:
        """Get papers with user status using JOIN approach.

        Args:
            skip: Number of records to skip
            limit: Maximum number of records to return
            language: Language for summaries

        Returns:
            List of PaperListItemResponse with papers, summaries, and user status
        """
        statement = self.join_query_builder.build_papers_with_user_status_join(
            skip=skip, limit=limit, language=language
        )

        result = self.db.exec(statement)
        rows = list(result.all())

        papers_with_status = []
        for row in rows:
            paper, summary, user_star, summary_read = row
            papers_with_status.append((paper, summary, user_star, summary_read))

        return papers_with_status

    def get_papers_with_relationships(
        self,
        skip: int = 0,
        limit: int = 100,
        language: str = "Korean",
    ) -> list[Paper]:
        """Get papers with their relationships (summaries, user stars, reads).

        Args:
            skip: Number of records to skip
            limit: Maximum number of records to return
            language: Language for summaries

        Returns:
            List of Paper objects with relationships loaded
        """
        papers = self.get_papers_with_overview_optimized(
            skip=skip, limit=limit, language=language
        )

        if not papers:
            return []

        # Fetch summaries for all papers
        summaries = self._fetch_summaries_for_papers(papers, language)

        # Attach summaries to papers (if needed for further processing)
        for paper in papers:
            if paper.paper_id in summaries:
                pass

        return papers

    def get_papers_with_user_status_efficient(
        self,
        user_id: int,
        skip: int = 0,
        limit: int = 100,
        language: str = "Korean",
    ) -> list[Paper]:
        """Get papers with user status using efficient approach.

        Args:
            user_id: User ID to get status for
            skip: Number of records to skip
            limit: Maximum number of records to return
            language: Language for summaries

        Returns:
            List of Paper objects
        """
        papers = self.get_papers_with_overview_optimized(
            skip=skip, limit=limit, language=language
        )

        if not papers:
            return []

        return papers

    def get_papers_with_overview(
        self,
        skip: int = 0,
        limit: int = 100,
        language: str = "Korean",
    ) -> list[Paper]:
        """Get papers with overview (alias for optimized method).

        Args:
            skip: Number of records to skip
            limit: Maximum number of records to return
            language: Language for summaries

        Returns:
            List of Paper objects
        """
        return self.get_papers_with_overview_optimized(
            skip=skip, limit=limit, language=language
        )

    def get_papers_by_status(
        self,
        status: PaperSummaryStatus,
        skip: int = 0,
        limit: int = 100,
    ) -> list[Paper]:
        """Get papers by summary status.

        Args:
            status: Summary status to filter by
            skip: Number of records to skip
            limit: Maximum number of records to return

        Returns:
            List of Paper objects with the specified status
        """
        statement = (
            select(Paper)
            .where(Paper.summary_status == status)
            .order_by(desc(Paper.updated_at))
            .offset(skip)
            .limit(limit)
        )

        result = self.db.exec(statement)
        return list(result.all())

    def update_summary_status(
        self,
        paper_id: PaperID,
        status: PaperSummaryStatus,
    ) -> Paper | None:
        """Update summary status for a paper.

        Args:
            paper_id: ID of the paper to update
            status: New summary status

        Returns:
            Updated Paper object if found, None otherwise
        """
        paper = self.get_by_id(paper_id)
        if paper:
            paper.summary_status = status
            self.db.add(paper)
            self.db.commit()
            self.db.refresh(paper)
        return paper

    def get_total_count(self) -> int:
        """Get total count of papers.

        Returns:
            Total number of papers in the database
        """
        from sqlmodel import func

        statement = select(func.count()).select_from(Paper)
        result = self.db.exec(statement)
        return result.first() or 0

    def create_from_arxiv_paper(self, arxiv_paper: Any) -> Paper:
        """Create a Paper from an arXiv paper object.

        Args:
            arxiv_paper: arXiv paper object

        Returns:
            Created Paper object
        """
        # Extract categories
        all_categories = []
        if hasattr(arxiv_paper, "categories") and arxiv_paper.categories:
            all_categories = arxiv_paper.categories.split()

        # Get primary category (first one)
        primary_category = all_categories[0] if all_categories else "Unknown"

        paper = Paper(
            arxiv_id=arxiv_paper.arxiv_id,
            title=arxiv_paper.title,
            abstract=arxiv_paper.abstract,
            primary_category=primary_category,
            categories=",".join(all_categories),
            authors=";".join(arxiv_paper.authors),
            url_abs=arxiv_paper.url_abs,
            url_pdf=arxiv_paper.url_pdf,
            published_at=arxiv_paper.published_date,
            summary_status=PaperSummaryStatus.BATCHED,
        )

        self.db.add(paper)
        self.db.commit()
        self.db.refresh(paper)
        return paper

    def create_papers_bulk(self, arxiv_papers: list[Any]) -> list[Paper]:
        """Create multiple papers from arXiv paper objects.

        Args:
            arxiv_papers: List of arXiv paper objects

        Returns:
            List of created Paper objects
        """
        papers: list[Paper] = []
        for arxiv_paper in arxiv_papers:
            # Extract categories
            all_categories = []
            if hasattr(arxiv_paper, "categories") and arxiv_paper.categories:
                all_categories = arxiv_paper.categories.split()

            # Get primary category (first one)
            primary_category = all_categories[0] if all_categories else "Unknown"

            paper = Paper(
                arxiv_id=arxiv_paper.arxiv_id,
                title=arxiv_paper.title,
                abstract=arxiv_paper.abstract,
                primary_category=primary_category,
                categories=",".join(all_categories),
                authors=";".join(arxiv_paper.authors),
                url_abs=arxiv_paper.url_abs,
                url_pdf=arxiv_paper.url_pdf,
                published_at=arxiv_paper.published_date,
                summary_status=PaperSummaryStatus.BATCHED,
            )
            papers.append(paper)

        self.db.add_all(papers)
        self.db.commit()

        # Refresh all papers to get their IDs
        for paper in papers:
            self.db.refresh(paper)

        return papers

    def update_summary_status_bulk(
        self,
        paper_ids: list[int],
        status: PaperSummaryStatus,
    ) -> int:
        """Update summary status for multiple papers.

        Args:
            paper_ids: List of paper IDs to update
            status: New summary status

        Returns:
            Number of papers updated
        """
        if not paper_ids:
            return 0

        statement = (
            update(Paper)
            .where(Paper.paper_id.in_(paper_ids))  # type: ignore[union-attr]
            .values(summary_status=status)
        )

        # Use the session's execute method for UPDATE statements
        self.db.execute(statement)
        return len(paper_ids)  # Return the number of papers we tried to update

    def get_papers_with_user_priority(
        self,
        user_id: int,
        skip: int = 0,
        limit: int = 100,
        language: str = "Korean",
        prioritize_summaries: bool = False,
        sort_by_relevance: bool = False,
        prioritize_starred: bool = False,
        prioritize_read: bool = False,
    ) -> list[Paper]:
        """Get papers with various user-based prioritization options.

        Args:
            user_id: User ID for star and read filtering
            skip: Number of records to skip
            limit: Maximum number of records to return
            language: Language for summaries
            prioritize_summaries: Whether to prioritize by summary status
            sort_by_relevance: Whether to sort by relevance score
            prioritize_starred: Whether to prioritize starred papers
            prioritize_read: Whether to prioritize read papers

        Returns:
            List of Paper objects with user-based prioritization
        """
        # Early exit: No user-based prioritization
        if not prioritize_starred and not prioritize_read:
            return self.get_papers_with_overview_optimized(
                skip=skip,
                limit=limit,
                language=language,
                prioritize_summaries=prioritize_summaries,
                sort_by_relevance=sort_by_relevance,
            )

        # Early exit: Combined star and read priority
        if prioritize_starred and prioritize_read:
            query = self.query_builder.build_combined_star_read_query(
                user_id=user_id,
                skip=skip,
                limit=limit,
                categories=None,
            )
            result = self.db.exec(query)
            return [paper for paper, _, _ in result.all()]

        # Early exit: Star priority only
        if prioritize_starred:
            star_query = self.query_builder.build_star_priority_query(
                user_id=user_id,
                skip=skip,
                limit=limit,
                categories=None,
            )
            star_result = self.db.exec(star_query)
            return [paper for paper, _ in star_result.all()]

        # Early exit: Read priority only
        if prioritize_read:
            read_query = self.query_builder.build_read_priority_query(
                user_id=user_id,
                skip=skip,
                limit=limit,
                categories=None,
            )
            read_result = self.db.exec(read_query)
            return [paper for paper, _ in read_result.all()]

        # Fallback to existing method
        return self.get_papers_with_overview_optimized(
            skip=skip,
            limit=limit,
            language=language,
            prioritize_summaries=prioritize_summaries,
            sort_by_relevance=sort_by_relevance,
        )
