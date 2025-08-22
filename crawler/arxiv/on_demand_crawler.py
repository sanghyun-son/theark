"""On-demand ArXiv crawler for user-initiated crawling requests."""

from dataclasses import dataclass
from typing import Any, Awaitable, Callable

from core import get_logger
from crawler.arxiv.constants import (
    DEFAULT_MONTHLY_PAPERS_LIMIT,
    DEFAULT_RECENT_PAPERS_LIMIT,
)
from crawler.arxiv.core import ArxivCrawlerCore, CrawlConfig, CrawlerStatus
from crawler.database import DatabaseManager, Paper

logger = get_logger(__name__)


@dataclass
class OnDemandCrawlConfig(CrawlConfig):
    """Configuration for on-demand crawler behavior."""

    # Crawl limits
    recent_papers_limit: int = DEFAULT_RECENT_PAPERS_LIMIT
    monthly_papers_limit: int = DEFAULT_MONTHLY_PAPERS_LIMIT


@dataclass
class OnDemandCrawlerStatus:
    """Status information for on-demand crawler."""

    type: str
    status: str
    core: CrawlerStatus
    config: dict[str, Any]


class OnDemandCrawler:
    """On-demand ArXiv crawler for user-initiated crawling requests."""

    def __init__(
        self,
        db_manager: DatabaseManager,
        config: OnDemandCrawlConfig | None = None,
        on_paper_crawled: Callable[[Paper], Awaitable[None]] | None = None,
        on_error: Callable[[Exception], Awaitable[None]] | None = None,
    ):
        """Initialize the on-demand crawler.

        Args:
            db_manager: Database manager for persistence
            config: Crawler configuration
            on_paper_crawled: Callback when paper is successfully crawled
            on_error: Callback when error occurs
        """
        self.config = config or OnDemandCrawlConfig()
        self.on_paper_crawled = on_paper_crawled
        self.on_error = on_error

        # Core crawler functionality
        self.core = ArxivCrawlerCore(
            db_manager=db_manager,
            config=self.config,
            on_paper_crawled=self._on_paper_crawled,
            on_error=self.on_error,
        )

        logger.info("OnDemandCrawler initialized")

    async def __aenter__(self) -> "OnDemandCrawler":
        """Async context manager entry."""
        await self.start()
        return self

    async def __aexit__(
        self,
        exc_type: type[BaseException] | None,
        exc_val: BaseException | None,
        exc_tb: Any,
    ) -> None:
        """Async context manager exit."""
        await self.stop()

    async def start(self) -> None:
        """Start the on-demand crawler."""
        await self.core.start()
        logger.info("OnDemandCrawler started")

    async def stop(self) -> None:
        """Stop the on-demand crawler."""
        await self.core.stop()
        logger.info("OnDemandCrawler stopped")

    async def crawl_single_paper(self, identifier: str) -> Paper | None:
        """Crawl a single paper by ID or URL.

        Args:
            identifier: arXiv ID, abstract URL, or PDF URL

        Returns:
            Crawled paper or None if failed
        """
        logger.info(f"On-demand crawling single paper: {identifier}")
        return await self.core.crawl_single_paper(identifier)

    async def crawl_papers_batch(self, identifiers: list[str]) -> list[Paper]:
        """Crawl multiple papers in a batch.

        Args:
            identifiers: List of arXiv IDs, abstract URLs, or PDF URLs

        Returns:
            List of successfully crawled papers
        """
        logger.info(f"On-demand crawling batch of {len(identifiers)} papers")
        return await self.core.crawl_papers_batch(identifiers)

    async def crawl_recent_papers(self, limit: int | None = None) -> list[Paper]:
        """Crawl the most recent papers (placeholder for future implementation).

        Args:
            limit: Maximum number of papers to crawl

        Returns:
            List of crawled papers
        """
        limit = limit or self.config.recent_papers_limit
        logger.info(f"On-demand crawling recent papers (limit: {limit})")

        # TODO: Implement recent papers crawling
        # This will use arXiv API to fetch recent papers in specific categories
        logger.warning("Recent papers crawling not yet implemented")
        return []

    async def crawl_monthly_papers(
        self, year: int, month: int, limit: int | None = None
    ) -> list[Paper]:
        """Crawl papers from a specific month (placeholder for future implementation).

        Args:
            year: Year to crawl
            month: Month to crawl (1-12)
            limit: Maximum number of papers to crawl

        Returns:
            List of crawled papers
        """
        limit = limit or self.config.monthly_papers_limit
        logger.info(
            f"On-demand crawling papers for {year}-{month:02d} (limit: {limit})"
        )

        # TODO: Implement monthly papers crawling
        # This will use arXiv API to fetch papers from specific month
        logger.warning("Monthly papers crawling not yet implemented")
        return []

    async def crawl_yearly_papers(
        self, year: int, limit: int | None = None
    ) -> list[Paper]:
        """Crawl papers from a specific year.

        Args:
            year: Year to crawl
            limit: Maximum number of papers to crawl

        Returns:
            List of crawled papers
        """
        limit = limit or (self.config.monthly_papers_limit * 12)
        logger.info(f"On-demand crawling papers for {year} (limit: {limit})")

        # For yearly strategy, crawl papers month by month
        total_papers = []
        remaining_limit = limit

        for month in range(1, 13):  # All 12 months
            if remaining_limit <= 0:
                break

            month_limit = min(remaining_limit, self.config.monthly_papers_limit)
            papers = await self.crawl_monthly_papers(
                year=year, month=month, limit=month_limit
            )

            total_papers.extend(papers)
            remaining_limit -= len(papers)

            logger.debug(f"Crawled {len(papers)} papers from {year}-{month:02d}")

        logger.info(f"On-demand crawled {len(total_papers)} papers from {year}")
        return total_papers

    async def get_status(self) -> OnDemandCrawlerStatus:
        """Get current crawler status and statistics.

        Returns:
            OnDemandCrawlerStatus with status information
        """
        core_status = await self.core.get_status()

        return OnDemandCrawlerStatus(
            type="on_demand",
            status="ready",
            core=core_status,
            config={
                "recent_papers_limit": self.config.recent_papers_limit,
                "monthly_papers_limit": self.config.monthly_papers_limit,
            },
        )

    async def _on_paper_crawled(self, paper: Paper) -> None:
        """Internal callback when paper is crawled.

        Args:
            paper: The crawled paper
        """
        # Forward to external callback if provided
        if self.on_paper_crawled:
            await self.on_paper_crawled(paper)
