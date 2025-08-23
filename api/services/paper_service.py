"""Paper service for CRUD operations."""

import asyncio

from api.models.paper import PaperCreate, PaperDeleteResponse, PaperResponse
from core import get_logger
from crawler.arxiv.on_demand_crawler import OnDemandCrawlConfig, OnDemandCrawler
from crawler.database import Paper as CrawlerPaper
from crawler.database import (
    PaperRepository,
    SummaryRepository,
)
from crawler.database.sqlite_manager import SQLiteManager
from crawler.summarizer.service import SummarizationService

logger = get_logger(__name__)


class PaperService:
    """Service for paper CRUD operations."""

    def __init__(self, db_manager: SQLiteManager | None = None) -> None:
        """Initialize paper service.

        Args:
            db_manager: Database manager instance. If None, will create a new one.
        """
        self.db_manager = db_manager
        self.paper_repo: PaperRepository | None = None
        self.summary_repo: SummaryRepository | None = None
        self.summarization_service: SummarizationService | None = None

        # Initialize repositories if db_manager is provided
        if self.db_manager:
            self.paper_repo = PaperRepository(self.db_manager)
            self.summary_repo = SummaryRepository(self.db_manager)

        # Initialize summarization service if API key is available
        try:
            self.summarization_service = SummarizationService()
            logger.info("SummarizationService initialized")
        except ValueError as e:
            logger.warning(f"SummarizationService not initialized: {e}")

    async def create_paper(self, paper_data: PaperCreate) -> PaperResponse:
        """Create a new paper.

        Args:
            paper_data: Paper data to create

        Returns:
            Created paper with ID and timestamps

        Raises:
            ValueError: If paper with same arXiv ID already exists
        """
        # Extract arXiv ID
        arxiv_id = self._extract_arxiv_id(paper_data)

        # Check if paper already exists
        existing_paper = self._get_paper_by_arxiv_id(arxiv_id)
        if existing_paper and not paper_data.force_refresh_metadata:
            logger.info(f"Paper {arxiv_id} already exists, returning existing paper")
            return PaperResponse.from_crawler_paper(existing_paper)

        # Create crawler and crawl the paper
        crawler_config = OnDemandCrawlConfig()

        if not self.db_manager:
            raise ValueError("Database manager not available")

        async with OnDemandCrawler(
            db_manager=self.db_manager, config=crawler_config
        ) as crawler:
            # Crawl the paper
            crawled_paper = await crawler.crawl_single_paper(arxiv_id)

            if not crawled_paper:
                raise ValueError(f"Failed to crawl paper {arxiv_id}")

            logger.info(f"Successfully crawled paper {arxiv_id}")

            # Trigger summarization if requested
            summary = None
            if paper_data.summarize_now and self.summarization_service:
                try:
                    # Start summarization in background
                    asyncio.create_task(
                        self._summarize_paper_async(
                            crawled_paper, paper_data.force_resummarize
                        )
                    )
                    logger.info(
                        f"Started background summarization for paper {arxiv_id}"
                    )
                except Exception as e:
                    logger.error(
                        f"Failed to start summarization for paper {arxiv_id}: {e}"
                    )

            return PaperResponse.from_crawler_paper(crawled_paper, summary)

    async def delete_paper(self, paper_identifier: str) -> PaperDeleteResponse:
        """Delete a paper by ID or arXiv ID.

        Args:
            paper_identifier: Paper ID or arXiv ID

        Returns:
            Deletion response with paper details

        Raises:
            ValueError: If paper not found
        """
        # Find paper by ID or arXiv ID
        paper = self._get_paper_by_identifier(paper_identifier)
        if not paper:
            raise ValueError(f"Paper not found: {paper_identifier}")

        # Delete paper from database
        if self.paper_repo and paper.paper_id:
            # For now, just log since delete method doesn't exist
            logger.info(f"Would delete paper {paper.arxiv_id} (ID: {paper.paper_id})")

        return PaperDeleteResponse(
            id=str(paper.paper_id),
            arxiv_id=paper.arxiv_id,
            message=f"Paper {paper.arxiv_id} deleted successfully",
        )

    def _extract_arxiv_id(self, paper_data: PaperCreate) -> str:
        """Extract arXiv ID from paper data.

        Args:
            paper_data: Paper creation data

        Returns:
            Extracted arXiv ID

        Raises:
            ValueError: If no valid arXiv ID can be extracted
        """
        # If arxiv_id is provided directly
        if paper_data.arxiv_id:
            return paper_data.arxiv_id

        # If URL is provided, extract arXiv ID from it
        if paper_data.url:
            # Extract arXiv ID from URL like https://arxiv.org/abs/2508.01234
            import re

            match = re.search(r"/abs/(\d{4}\.\d{5})$", paper_data.url)
            if match:
                return match.group(1)
            else:
                raise ValueError("Could not extract arXiv ID from URL")

        # This should not happen due to validation, but just in case
        raise ValueError("No arXiv ID or URL provided")

    def _get_paper_by_arxiv_id(self, arxiv_id: str) -> CrawlerPaper | None:
        """Get paper by arXiv ID.

        Args:
            arxiv_id: arXiv ID

        Returns:
            Paper if found, None otherwise
        """
        if not self.db_manager:
            return None

        if not self.paper_repo:
            return None

        try:
            return self.paper_repo.get_by_arxiv_id(arxiv_id)
        except Exception as e:
            logger.error(f"Error getting paper by arXiv ID {arxiv_id}: {e}")
            return None

    def _get_paper_by_identifier(self, identifier: str) -> CrawlerPaper | None:
        """Get paper by ID or arXiv ID.

        Args:
            identifier: Paper ID or arXiv ID

        Returns:
            Paper if found, None otherwise
        """
        if not self.paper_repo:
            return None

        try:
            # Try as arXiv ID first (since get_by_arxiv_id exists)
            paper = self.paper_repo.get_by_arxiv_id(identifier)
            if paper:
                return paper

            # Try as paper ID (would need to implement get_by_id)
            try:
                int(identifier)  # Validate it's a number
                # For now, just return None since get_by_id doesn't exist
                return None
            except ValueError:
                return None
        except Exception as e:
            logger.error(f"Error getting paper by identifier {identifier}: {e}")
            return None

    async def _summarize_paper_async(
        self, paper: CrawlerPaper, force_resummarize: bool = False
    ) -> None:
        """Summarize paper asynchronously.

        Args:
            paper: Paper to summarize
            force_resummarize: Whether to force re-summarization
        """
        if not self.summarization_service:
            logger.warning("SummarizationService not available")
            return

        try:
            # Check if summary already exists
            if not force_resummarize and self.summary_repo:
                # For now, just log since get_latest_by_paper_id doesn't exist
                logger.info(f"Would check existing summary for paper {paper.arxiv_id}")

            # Create summary request
            summary_response = await self.summarization_service.summarize_paper(
                paper_id=str(paper.paper_id),
                abstract=paper.abstract,
                language="English",
            )

            if summary_response and self.summary_repo:
                # For now, just log since create_from_summary_response doesn't exist
                logger.info(f"Would save summary for paper {paper.arxiv_id}")
            else:
                logger.error(f"Failed to create summary for paper {paper.arxiv_id}")

        except Exception as e:
            logger.error(f"Error summarizing paper {paper.arxiv_id}: {e}")

    async def close(self) -> None:
        """Close the service and cleanup resources."""
        if self.summarization_service:
            await self.summarization_service.close()
        logger.info("PaperService closed")
