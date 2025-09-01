"""ArXiv storage manager for paper metadata storage."""

from typing import Any

from sqlmodel import Session, select

from core.log import get_logger
from core.models.domain.arxiv import ArxivPaper
from core.models.rows import ArxivFailedPaper, Paper
from core.types import PaperSummaryStatus
from core.utils import get_current_timestamp

logger = get_logger(__name__)


class ArxivStorageManager:
    """Manager for storing ArXiv paper metadata in the database."""

    def __init__(self, engine: Any) -> None:
        """Initialize the storage manager.

        Args:
            engine: Database engine
        """
        self.engine = engine

    async def store_paper_metadata(self, paper: ArxivPaper) -> Paper | None:
        """Store paper metadata in the database with batched status.

        Args:
            paper: ArxivPaper object to store

        Returns:
            Created Paper object or None if already exists
        """
        # Extract ArXiv-specific information from ArxivPaper
        arxiv_id = paper.arxiv_id
        primary_category = paper.primary_category
        all_categories = paper.categories

        with Session(self.engine) as session:
            # Check if paper already exists
            existing_paper = session.exec(
                select(Paper).where(Paper.arxiv_id == arxiv_id)
            ).first()

            if existing_paper is not None:
                logger.warning(
                    f"Paper with arxiv_id {arxiv_id} already exists, skipping"
                )
                return None

            # Create new paper record with batched status
            db_paper = Paper(
                arxiv_id=arxiv_id,
                title=paper.title,
                abstract=paper.abstract,
                primary_category=primary_category,
                categories=",".join(all_categories),
                authors=";".join(paper.authors),
                url_abs=paper.url_abs,
                url_pdf=paper.url_pdf,
                published_at=paper.published_date,
                summary_status=PaperSummaryStatus.BATCHED,
            )

            session.add(db_paper)
            session.commit()
            session.refresh(db_paper)

            logger.info(
                f"Stored paper metadata: {arxiv_id} "
                f"({paper.title[:50]}...) "
                f"with categories: {db_paper.categories}"
            )

            return db_paper

    async def store_papers_batch(self, papers: list[ArxivPaper]) -> int:
        """Store multiple papers in batch.

        Args:
            papers: List of ArxivPaper objects to store

        Returns:
            Number of successfully stored papers
        """
        stored_count = 0

        for paper in papers:
            try:
                stored_paper = await self.store_paper_metadata(paper)
                if stored_paper:
                    stored_count += 1
            except Exception as e:
                logger.warning(f"Failed to store paper {paper.arxiv_id}: {e}")
                await self.handle_failed_paper(
                    paper.arxiv_id, paper.primary_category, str(e)
                )

        return stored_count

    async def handle_failed_paper(
        self, arxiv_id: str, category: str, error_message: str
    ) -> None:
        """Handle a failed paper by storing it in the failed papers table.

        Args:
            arxiv_id: ArXiv ID of the failed paper
            category: ArXiv category
            error_message: Error message describing the failure
        """
        with Session(self.engine) as session:
            # Check if this paper is already in the failed papers table
            existing_failed = session.exec(
                select(ArxivFailedPaper).where(ArxivFailedPaper.arxiv_id == arxiv_id)
            ).first()

            if existing_failed is not None:
                # Update existing failed paper record
                existing_failed.retry_count += 1
                existing_failed.last_retry_at = get_current_timestamp()
                existing_failed.error_message = error_message
                logger.info(
                    f"Updated failed paper {arxiv_id} (retry #{existing_failed.retry_count}): "
                    f"{error_message}"
                )
            else:
                # Create new failed paper record
                failed_paper = ArxivFailedPaper(
                    arxiv_id=arxiv_id,
                    category=category,
                    error_message=error_message,
                    retry_count=0,
                )
                session.add(failed_paper)
                logger.info(f"Stored failed paper {arxiv_id}: {error_message}")

            session.commit()
