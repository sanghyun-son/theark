"""Paper repository using SQLModel with dependency injection."""

from typing import Any

from sqlmodel import Session, desc, func, select

from core.database.repository.base import BaseRepository
from core.database.repository.summary import SummaryRepository
from core.database.repository.summary_read import SummaryReadRepository
from core.database.repository.user import UserStarRepository
from core.log import get_logger
from core.models.api.responses import PaperListItemResponse
from core.models.rows import Paper, Summary, SummaryRead, UserStar
from core.types import PaperSummaryStatus

logger = get_logger(__name__)


class PaperRepository(BaseRepository[Paper]):
    """Paper repository using SQLModel with dependency injection."""

    def __init__(self, db: Session) -> None:
        """Initialize paper repository."""
        super().__init__(Paper, db)

    def get_by_arxiv_id(self, arxiv_id: str) -> Paper | None:
        """Get paper by arXiv ID.

        Args:
            arxiv_id: arXiv ID

        Returns:
            Paper if found, None otherwise
        """
        statement = select(Paper).where(Paper.arxiv_id == arxiv_id)
        result = self.db.exec(statement)
        return result.first()

    def get_papers_with_summaries(
        self,
        skip: int = 0,
        limit: int = 100,
        language: str | None = None,
    ) -> list[Paper]:
        """Get papers with their summaries.

        Args:
            skip: Number of records to skip
            limit: Maximum number of records to return
            language: Filter by summary language

        Returns:
            List of papers with summaries
        """
        # Start with base query - order by updated_at DESC (latest first)
        statement = (
            select(Paper).order_by(desc(Paper.updated_at)).offset(skip).limit(limit)
        )
        result = self.db.exec(statement)
        papers = list(result.all())

        # If language filter is specified, filter papers that have summaries in that language
        if language:
            # For now, just return all papers since we removed the Summary import
            # This can be enhanced later when needed
            return papers

        return papers

    def get_papers_with_overview_optimized(
        self,
        skip: int = 0,
        limit: int = 100,
        language: str | None = None,
    ) -> list[PaperListItemResponse]:
        """Get papers with overview only, optimized with batch queries to avoid N+1 queries.

        Args:
            skip: Number of records to skip
            limit: Maximum number of records to return
            language: Filter by summary language

        Returns:
            List of tuples: (Paper, overview, has_summary, relevance)
        """
        # Get papers first
        statement = (
            select(Paper).order_by(desc(Paper.updated_at)).offset(skip).limit(limit)
        )
        result = self.db.exec(statement)
        papers = list(result.all())

        if not papers:
            return []

        # Get all paper IDs
        paper_ids = [paper.paper_id for paper in papers if paper.paper_id]

        # Batch fetch summaries for all papers
        summaries = {}
        if paper_ids:
            if language:
                # Get summaries for specific language
                summary_statement = select(Summary).where(
                    (Summary.paper_id.in_(paper_ids))  # type: ignore
                    & (Summary.language == language)
                )
                summary_results = self.db.exec(summary_statement).all()
                summaries = {s.paper_id: s for s in summary_results}

                # If no summaries found and language is not English, try English fallback
                if not summaries and language != "English":
                    fallback_statement = select(Summary).where(
                        (Summary.paper_id.in_(paper_ids))  # type: ignore
                        & (Summary.language == "English")
                    )
                    fallback_results = self.db.exec(fallback_statement).all()
                    summaries = {s.paper_id: s for s in fallback_results}
            else:
                # Get all summaries
                summary_statement = select(Summary).where(
                    Summary.paper_id.in_(paper_ids)  # type: ignore
                )
                summary_results = self.db.exec(summary_statement).all()
                summaries = {s.paper_id: s for s in summary_results}

        # Process results
        paper_overview_data = []
        for paper in papers:
            summary = summaries.get(paper.paper_id)
            overview = summary.overview if summary else None
            relevance = summary.relevance if summary else None
            has_summary = summary is not None

            paper_overview_data.append(
                PaperListItemResponse.from_paper_with_overview(
                    paper=paper,
                    overview=overview,
                    has_summary=has_summary,
                    relevance=relevance,
                )
            )

        return paper_overview_data

    def get_papers_with_summaries_join(
        self,
        skip: int = 0,
        limit: int = 100,
        language: str | None = None,
    ) -> list[PaperListItemResponse]:
        """Get papers with summaries using SQL JOIN for maximum efficiency.

        This method uses SQLModel's JOIN functionality to fetch papers and summaries
        in a single query, eliminating the need for separate batch queries.

        Args:
            skip: Number of records to skip
            limit: Maximum number of records to return
            language: Filter by summary language

        Returns:
            List of PaperListItemResponse with papers and their summaries
        """
        if language:
            # Use LEFT JOIN to get all papers and their summaries for specific language
            statement = (
                select(Paper, Summary)
                .join(Summary, isouter=True)
                .where(Summary.language == language)
                .order_by(desc(Paper.updated_at))
                .offset(skip)
                .limit(limit)
            )
        else:
            # Get all papers with their summaries (no language filter)
            statement = (
                select(Paper, Summary)
                .join(Summary, isouter=True)
                .order_by(desc(Paper.updated_at))
                .offset(skip)
                .limit(limit)
            )

        result = self.db.exec(statement)
        rows = list(result.all())

        # Process results using from_paper_summary_row
        paper_responses = []
        for row in rows:
            paper_response = PaperListItemResponse.from_paper_summary_row(row)
            paper_responses.append(paper_response)

        return paper_responses

    def get_papers_with_user_status_join(
        self,
        user_id: int,
        skip: int = 0,
        limit: int = 100,
        language: str | None = None,
    ) -> list[PaperListItemResponse]:
        """Get papers with summaries and user status using multiple JOINs.

        This method uses multiple JOINs to fetch papers, summaries, and user status
        (star/read) in a single query for maximum efficiency.

        Args:
            user_id: User ID for star/read status
            skip: Number of records to skip
            limit: Maximum number of records to return
            language: Filter by summary language

        Returns:
            List of PaperListItemResponse with papers, summaries, and user status
        """
        # Build the base query with multiple JOINs
        if language:
            statement = (
                select(Paper, Summary, UserStar, SummaryRead)
                .join(Summary, isouter=True)
                .join(UserStar, isouter=True)
                .join(SummaryRead, isouter=True)
                .where(Summary.language == language)
                .order_by(desc(Paper.updated_at))
                .offset(skip)
                .limit(limit)
            )
        else:
            statement = (
                select(Paper, Summary, UserStar, SummaryRead)
                .join(Summary, isouter=True)
                .join(UserStar, isouter=True)
                .join(SummaryRead, isouter=True)
                .order_by(desc(Paper.updated_at))
                .offset(skip)
                .limit(limit)
            )

        result = self.db.exec(statement)
        rows = list(result.all())

        # Process results using from_full_joined_row
        paper_responses = []
        for row in rows:
            paper_response = PaperListItemResponse.from_full_joined_row(row)
            paper_responses.append(paper_response)

        return paper_responses

    def get_papers_with_relationships(
        self,
        skip: int = 0,
        limit: int = 100,
        language: str | None = None,
        user_id: int | None = None,
    ) -> list[PaperListItemResponse]:
        """Get papers with relationships using SQLModel's relationship attributes.

        This method leverages SQLModel's relationship attributes for efficient
        data loading with proper eager loading.

        Args:
            skip: Number of records to skip
            limit: Maximum number of records to return
            language: Filter by summary language
            user_id: User ID for filtering user-specific data

        Returns:
            List of PaperListItemResponse with papers and their relationships
        """
        # Build base query with relationships
        statement = (
            select(Paper).order_by(desc(Paper.updated_at)).offset(skip).limit(limit)
        )

        result = self.db.exec(statement)
        papers = list(result.all())

        if not papers:
            return []

        # Load relationships efficiently
        paper_overview_data = []
        for paper in papers:
            # Get summaries for this paper
            summaries = []
            if paper.summaries:  # Use relationship attribute
                summaries = (
                    [s for s in paper.summaries if s.language == language]
                    if language
                    else paper.summaries
                )

            # Find the best summary
            best_summary = None
            if summaries:
                if language:
                    best_summary = next(
                        (s for s in summaries if s.language == language), None
                    )
                    if not best_summary and language != "English":
                        best_summary = next(
                            (s for s in summaries if s.language == "English"), None
                        )
                else:
                    best_summary = summaries[0]

            overview = best_summary.overview if best_summary else None
            relevance = best_summary.relevance if best_summary else None
            has_summary = best_summary is not None

            paper_overview_data.append(
                PaperListItemResponse.from_paper_with_overview(
                    paper=paper,
                    overview=overview,
                    has_summary=has_summary,
                    relevance=relevance,
                )
            )

        return paper_overview_data

    def get_papers_with_user_status_efficient(
        self,
        user_id: int,
        skip: int = 0,
        limit: int = 100,
        language: str | None = None,
    ) -> list[PaperListItemResponse]:
        """Get papers with user status using efficient batch queries.

        This method combines the best of both worlds: efficient batch queries
        for summaries and user status, avoiding the complexity of complex JOINs.

        Args:
            user_id: User ID for star/read status
            skip: Number of records to skip
            limit: Maximum number of records to return
            language: Filter by summary language

        Returns:
            List of PaperListItemResponse with papers, summaries, and user status
        """
        # Get papers with summaries using batch optimization
        paper_overview_data = self.get_papers_with_overview_optimized(
            skip=skip, limit=limit, language=language
        )

        if not paper_overview_data:
            return []

        # Get all paper IDs for batch user status queries
        paper_ids = [data.paper_id for data in paper_overview_data if data.paper_id]

        # Batch fetch all user status in parallel
        star_repo = UserStarRepository(self.db)
        summary_read_repo = SummaryReadRepository(self.db)
        summary_repo = SummaryRepository(self.db)

        # Get starred papers
        starred_paper_ids = set(star_repo.get_starred_paper_ids(user_id, paper_ids))

        # Get summaries for papers that have them
        summary_paper_ids = [
            data.paper_id
            for data in paper_overview_data
            if data.paper_id and data.has_summary
        ]

        summaries = {}
        if summary_paper_ids:
            summaries = summary_repo.get_by_paper_ids_and_language(
                summary_paper_ids, language or "Korean"
            )

        # Get read summary IDs
        summary_ids = [s.summary_id for s in summaries.values() if s.summary_id]
        read_summary_ids = set()
        if summary_ids:
            read_summary_ids = set(
                summary_read_repo.get_read_summary_ids(user_id, summary_ids)
            )

        # Update paper overview data with user status
        for overview_data in paper_overview_data:
            paper_id = overview_data.paper_id
            if paper_id:
                # Add user status to the overview data
                overview_data.is_starred = paper_id in starred_paper_ids

                if overview_data.has_summary:
                    summary = summaries.get(paper_id)
                    if summary and summary.summary_id:
                        overview_data.is_read = summary.summary_id in read_summary_ids
                    else:
                        overview_data.is_read = False
                else:
                    overview_data.is_read = False

        return paper_overview_data

    def get_papers_with_overview(
        self,
        skip: int = 0,
        limit: int = 100,
        language: str | None = None,
    ) -> list[PaperListItemResponse]:
        """Get papers with overview only, not full summaries.

        Args:
            skip: Number of records to skip
            limit: Maximum number of records to return
            language: Filter by summary language

        Returns:
            List of tuples: (Paper, overview, has_summary, relevance)
        """
        # Use optimized version
        return self.get_papers_with_overview_optimized(skip, limit, language)

    def get_papers_by_status(
        self, status: str, skip: int = 0, limit: int = 100
    ) -> list[Paper]:
        """Get papers by summary status.

        Args:
            status: Summary status (batched, processing, done)
            skip: Number of records to skip
            limit: Maximum number of records to return

        Returns:
            List of papers with specified status
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
        paper_id: int,
        status: PaperSummaryStatus,
    ) -> bool:
        """Update paper summary status.

        Args:
            paper_id: Paper ID
            status: New status

        Returns:
            True if updated, False if not found
        """
        statement = select(Paper).where(Paper.paper_id == paper_id)
        result = self.db.exec(statement)
        paper = result.first()

        if paper:
            paper.summary_status = status
            self.db.commit()
            self.db.refresh(paper)
            return True

        return False

    def get_total_count(self) -> int:
        """Get total number of papers in the database.

        Returns:
            Total count of papers
        """
        stmt = select(func.count()).select_from(Paper)
        return self.db.exec(stmt).one()

    def create_from_arxiv_paper(self, arxiv_paper: Any) -> Paper:
        """Create a Paper from an ArxivPaper object.

        Args:
            arxiv_paper: ArxivPaper object

        Returns:
            Created Paper object
        """

        # Extract ArXiv-specific information from ArxivPaper
        arxiv_id = arxiv_paper.arxiv_id
        primary_category = arxiv_paper.primary_category
        all_categories = arxiv_paper.categories

        # Create new paper record with batched status
        db_paper = Paper(
            arxiv_id=arxiv_id,
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

        self.db.add(db_paper)
        self.db.commit()
        self.db.refresh(db_paper)

        logger.info(
            f"Created paper: {arxiv_id} "
            f"({arxiv_paper.title[:50]}...) "
            f"with categories: {db_paper.categories}"
        )

        return db_paper
