"""ArXiv crawler combining on-demand and periodic crawling capabilities."""

from dataclasses import dataclass
from enum import Enum
from typing import Any, Awaitable, Callable

from core import get_logger
from core.models.database.entities import PaperEntity
from crawler.arxiv.core import SummarizationConfig
from crawler.arxiv.on_demand_crawler import (
    OnDemandCrawlConfig,
    OnDemandCrawler,
    OnDemandCrawlerStatus,
)
from crawler.arxiv.periodic_crawler import (
    PeriodicCrawlConfig,
    PeriodicCrawler,
    PeriodicCrawlerStatus,
)
from crawler.database import DatabaseManager

logger = get_logger(__name__)


class CrawlStatus(Enum):
    """Status of crawl operations."""

    IDLE = "idle"
    RUNNING = "running"
    PAUSED = "paused"
    STOPPED = "stopped"
    ERROR = "error"


@dataclass
class CrawlConfig:
    """Configuration for the combined crawler."""

    # On-demand crawler settings
    on_demand: OnDemandCrawlConfig | None = None

    # Periodic crawler settings
    periodic: PeriodicCrawlConfig | None = None

    def __post_init__(self) -> None:
        """Initialize default configs if not provided."""
        if self.on_demand is None:
            self.on_demand = OnDemandCrawlConfig()
        if self.periodic is None:
            self.periodic = PeriodicCrawlConfig()

        # Ensure summarization config is set
        if self.on_demand.summarization is None:
            self.on_demand.summarization = SummarizationConfig()
        if self.periodic.summarization is None:
            self.periodic.summarization = SummarizationConfig()


@dataclass
class ArxivCrawlerStatus:
    """Status information for the combined ArXiv crawler."""

    status: str
    on_demand: OnDemandCrawlerStatus
    periodic: PeriodicCrawlerStatus
    background_task_running: bool


class ArxivCrawler:
    """ArXiv crawler combining on-demand and periodic crawling capabilities."""

    def __init__(
        self,
        db_manager: DatabaseManager,
        config: CrawlConfig | None = None,
        on_paper_crawled: Callable[[PaperEntity], Awaitable[None]] | None = None,
        on_error: Callable[[Exception], Awaitable[None]] | None = None,
    ):
        """Initialize ArXiv crawler.

        Args:
            db_manager: Database manager for persistence
            config: Crawler configuration
            on_paper_crawled: Callback when paper is successfully crawled
            on_error: Callback when error occurs
        """
        self.db_manager = db_manager
        self.config = config or CrawlConfig()
        self.on_paper_crawled = on_paper_crawled
        self.on_error = on_error

        # State management
        self.status = CrawlStatus.IDLE

        # On-demand crawler
        self.on_demand_crawler = OnDemandCrawler(
            config=self.config.on_demand,
            on_paper_crawled=self._on_paper_crawled,
            on_error=self.on_error,
        )

        # Periodic crawler
        self.periodic_crawler = PeriodicCrawler(
            db_manager=db_manager,
            config=self.config.periodic,
            on_paper_crawled=self._on_paper_crawled,
            on_error=self.on_error,
        )

        logger.info("ArxivCrawler initialized")

    async def __aenter__(self) -> "ArxivCrawler":
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
        """Start the crawler and initialize components."""
        if self.status != CrawlStatus.IDLE:
            logger.warning(f"Crawler already in {self.status} state")
            return

        try:
            # Start both crawlers
            await self.on_demand_crawler.start()
            await self.periodic_crawler.start()

            # Update status
            self.status = CrawlStatus.IDLE

            logger.info("ArXivCrawler started successfully")

        except Exception as e:
            self.status = CrawlStatus.ERROR
            logger.error(f"Failed to start crawler: {e}")
            if self.on_error:
                await self.on_error(e)
            raise

    async def stop(self) -> None:
        """Stop the crawler and cleanup resources."""
        logger.info("Stopping ArXivCrawler...")

        # Stop both crawlers
        await self.on_demand_crawler.stop()
        await self.periodic_crawler.stop()

        # Update status
        self.status = CrawlStatus.STOPPED
        logger.info("ArXivCrawler stopped")

    async def start_background_loop(self) -> None:
        """Start the background crawling loop."""
        await self.periodic_crawler.start_monitoring()
        self.status = CrawlStatus.RUNNING
        logger.info("Background crawling loop started")

    async def stop_background_loop(self) -> None:
        """Stop the background crawling loop."""
        await self.periodic_crawler.stop_monitoring()
        self.status = CrawlStatus.PAUSED
        logger.info("Background crawling loop stopped")

    async def crawl_single_paper(
        self, identifier: str, db_manager: DatabaseManager
    ) -> PaperEntity | None:
        """Crawl a single paper by ID or URL.

        Args:
            identifier: arXiv ID, abstract URL, or PDF URL
            db_manager: Database manager instance

        Returns:
            Crawled paper or None if failed
        """
        return await self.on_demand_crawler.crawl_single_paper(identifier, db_manager)

    async def crawl_recent_papers(self, limit: int | None = None) -> list[PaperEntity]:
        """Crawl the most recent papers.

        Args:
            limit: Maximum number of papers to crawl

        Returns:
            List of crawled papers
        """
        return await self.on_demand_crawler.crawl_recent_papers(limit)

    async def crawl_monthly_papers(
        self, year: int, month: int, limit: int | None = None
    ) -> list[PaperEntity]:
        """Crawl papers from a specific month.

        Args:
            year: Year to crawl
            month: Month to crawl (1-12)
            limit: Maximum number of papers to crawl

        Returns:
            List of crawled papers
        """
        return await self.on_demand_crawler.crawl_monthly_papers(year, month, limit)

    async def crawl_yearly_papers(
        self, year: int, limit: int | None = None
    ) -> list[PaperEntity]:
        """Crawl papers from a specific year.

        Args:
            year: Year to crawl
            limit: Maximum number of papers to crawl

        Returns:
            List of crawled papers
        """
        return await self.on_demand_crawler.crawl_yearly_papers(year, limit)

    async def get_status(self) -> ArxivCrawlerStatus:
        """Get current crawler status and statistics.

        Returns:
            ArxivCrawlerStatus with status information
        """
        on_demand_status = await self.on_demand_crawler.get_status()
        periodic_status = await self.periodic_crawler.get_status()

        return ArxivCrawlerStatus(
            status=self.status.value,
            on_demand=on_demand_status,
            periodic=periodic_status,
            background_task_running=periodic_status.monitoring_active,
        )

    async def _on_paper_crawled(self, paper: PaperEntity) -> None:
        """Internal callback when paper is crawled.

        Args:
            paper: The crawled paper
        """
        # Forward to external callback if provided
        if self.on_paper_crawled:
            await self.on_paper_crawled(paper)
