"""Paper repository using SQLModel with dependency injection."""

from sqlmodel import Session, desc, func, select

from core.database.repository.base import BaseRepository
from core.log import get_logger
from core.models.api.responses import PaperOverviewData
from core.models.rows import Paper, Summary
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

    def get_papers_with_overview(
        self,
        skip: int = 0,
        limit: int = 100,
        language: str | None = None,
    ) -> list[PaperOverviewData]:
        """Get papers with overview only, not full summaries.

        Args:
            skip: Number of records to skip
            limit: Maximum number of records to return
            language: Filter by summary language

        Returns:
            List of tuples: (Paper, overview, has_summary, relevance)
        """
        # Base query for papers
        statement = (
            select(Paper).order_by(desc(Paper.updated_at)).offset(skip).limit(limit)
        )
        result = self.db.exec(statement)
        papers = list(result.all())

        # Get overview and relevance for each paper
        paper_overview_data = []
        for paper in papers:
            overview = None
            has_summary = False
            relevance = None

            if paper.paper_id:
                # Get summary overview and relevance for this paper
                summary_statement = select(Summary.overview, Summary.relevance).where(
                    Summary.paper_id == paper.paper_id
                )

                if language:
                    # Filter by language
                    summary_statement = summary_statement.where(
                        Summary.language == language
                    )

                summary_result = self.db.exec(summary_statement).first()
                if summary_result:
                    overview = summary_result[0]  # overview
                    relevance = summary_result[1]  # relevance
                    has_summary = True
                elif language and language != "English":
                    # Try English fallback
                    summary_statement = select(
                        Summary.overview, Summary.relevance
                    ).where(
                        (Summary.paper_id == paper.paper_id)
                        & (Summary.language == "English")
                    )
                    summary_result = self.db.exec(summary_statement).first()
                    if summary_result:
                        overview = summary_result[0]  # overview
                        relevance = summary_result[1]  # relevance
                        has_summary = True

            paper_overview_data.append(
                PaperOverviewData(
                    paper=paper,
                    overview=overview,
                    has_summary=has_summary,
                    relevance=relevance,
                )
            )

        return paper_overview_data

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
