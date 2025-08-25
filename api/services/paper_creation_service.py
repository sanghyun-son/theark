"""Paper creation service for handling paper creation logic."""

from core import get_logger
from core.models import PaperCreateRequest as PaperCreate
from core.models.database.entities import PaperEntity
from crawler.arxiv.client import ArxivClient
from crawler.arxiv.on_demand_crawler import OnDemandCrawlConfig, OnDemandCrawler
from crawler.database import PaperRepository
from crawler.database.sqlite_manager import SQLiteManager

logger = get_logger(__name__)


class PaperCreationService:
    """Service for paper creation operations."""

    def __init__(self) -> None:
        """Initialize paper creation service."""
        pass

    def _extract_arxiv_id(self, paper_data: PaperCreate) -> str:
        """Extract arXiv ID from paper data."""
        if not paper_data.url:
            raise ValueError("No URL provided")

        # Extract arXiv ID from URL
        import re

        match = re.search(r"arxiv\.org/(?:abs|pdf)/(\d{4}\.\d{4,5})", paper_data.url)
        if not match:
            raise ValueError("Invalid arXiv URL format")

        return match.group(1)

    def _get_paper_by_arxiv_id(
        self, arxiv_id: str, paper_repo: PaperRepository
    ) -> PaperEntity | None:
        """Get paper by arXiv ID."""
        return paper_repo.get_by_arxiv_id(arxiv_id)

    async def create_paper(
        self,
        paper_data: PaperCreate,
        db_manager: SQLiteManager,
        arxiv_client: ArxivClient,
    ) -> PaperEntity:
        """Create a paper with injected ArxivClient."""
        arxiv_id = self._extract_arxiv_id(paper_data)

        paper_repo = PaperRepository(db_manager)

        # Check if paper already exists
        existing_paper = self._get_paper_by_arxiv_id(arxiv_id, paper_repo)
        if existing_paper:
            logger.info(f"Paper {arxiv_id} already exists, returning existing paper")
            return existing_paper

        # Crawl the paper with injected client
        crawled_paper = await self._crawl_paper(arxiv_id, db_manager, arxiv_client)
        return crawled_paper

    async def _crawl_paper(
        self,
        arxiv_id: str,
        db_manager: SQLiteManager,
        arxiv_client: ArxivClient,
    ) -> PaperEntity:
        """Crawl a single paper from arXiv."""
        crawler_config = OnDemandCrawlConfig()
        async with OnDemandCrawler(config=crawler_config) as crawler:
            crawled_paper = await crawler.crawl_single_paper(
                arxiv_id, db_manager, arxiv_client
            )
            if not crawled_paper:
                raise ValueError(f"Failed to crawl paper {arxiv_id}")

            logger.info(f"Successfully crawled paper {arxiv_id}")
            return crawled_paper

    def get_paper_by_identifier(
        self, paper_identifier: str, db_manager: SQLiteManager
    ) -> PaperEntity | None:
        """Get paper by ID or arXiv ID."""
        paper_repo = PaperRepository(db_manager)

        # Try to get by arXiv ID first
        paper = paper_repo.get_by_arxiv_id(paper_identifier)
        if paper:
            return paper

        # Try to get by paper ID
        try:
            paper_id = int(paper_identifier)
            return paper_repo.get_by_id(paper_id)
        except ValueError:
            return None
