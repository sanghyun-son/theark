"""Periodic ArXiv crawler for background monitoring of new papers."""

from dataclasses import dataclass
from typing import Any, Awaitable, Callable

from core import PeriodicTask, PeriodicTaskManager, get_logger
from core.models.database.entities import PaperEntity
from crawler.arxiv.constants import (
    DEFAULT_BACKGROUND_INTERVAL,
    DEFAULT_RECENT_PAPERS_LIMIT,
)
from crawler.arxiv.core import ArxivCrawlerCore, CrawlConfig, CrawlerStatus
from crawler.database import DatabaseManager

logger = get_logger(__name__)


@dataclass
class PeriodicCrawlConfig(CrawlConfig):
    """Configuration for periodic crawler behavior."""

    # Background loop settings
    background_interval: int = DEFAULT_BACKGROUND_INTERVAL

    # Crawl limits
    recent_papers_limit: int = DEFAULT_RECENT_PAPERS_LIMIT


@dataclass
class PeriodicCrawlerStatus:
    """Status information for periodic crawler."""

    type: str
    status: str
    core: CrawlerStatus
    config: dict[str, Any]
    monitoring: dict[str, Any] | None = None
    monitoring_active: bool = False


class RecentPapersMonitorTask(PeriodicTask):
    """Periodic task for monitoring recent papers."""

    def __init__(
        self,
        core: ArxivCrawlerCore,
        limit: int = DEFAULT_RECENT_PAPERS_LIMIT,
    ):
        """Initialize the recent papers monitor task.

        Args:
            core: Core crawler functionality
            limit: Maximum number of papers to check per iteration
        """
        self.core = core
        self.limit = limit

        logger.info(f"RecentPapersMonitorTask initialized with limit: {limit}")

    async def execute(self) -> None:
        """Execute the periodic monitoring task."""
        logger.info(f"Executing recent papers monitoring (limit: {self.limit})")

        # TODO: Implement recent papers monitoring
        # This will:
        # 1. Query arXiv API for recent papers
        # 2. Check which ones are not in our database
        # 3. Crawl only the new papers
        logger.warning("Recent papers monitoring not yet implemented")

    async def on_start(self) -> None:
        """Called when the periodic task starts."""
        logger.info("Recent papers monitoring task starting")

    async def on_stop(self) -> None:
        """Called when the periodic task stops."""
        logger.info("Recent papers monitoring task stopping")

    async def on_error(self, error: Exception) -> None:
        """Handle errors during periodic monitoring."""
        logger.error(f"Error in recent papers monitoring task: {error}")


class PeriodicCrawler:
    """Periodic ArXiv crawler for background monitoring of new papers."""

    def __init__(
        self,
        db_manager: DatabaseManager,
        config: PeriodicCrawlConfig | None = None,
        on_paper_crawled: Callable[[PaperEntity], Awaitable[None]] | None = None,
        on_error: Callable[[Exception], Awaitable[None]] | None = None,
    ):
        """Initialize the periodic crawler.

        Args:
            db_manager: Database manager for persistence
            config: Crawler configuration
            on_paper_crawled: Callback when paper is successfully crawled
            on_error: Callback when error occurs
        """
        self.config = config or PeriodicCrawlConfig()
        self.on_paper_crawled = on_paper_crawled
        self.on_error = on_error

        # Core crawler functionality
        self.core = ArxivCrawlerCore(
            db_manager=db_manager,
            config=self.config,
            on_paper_crawled=self._on_paper_crawled,
            on_error=self.on_error,
        )

        # Periodic task manager
        self._task_manager: PeriodicTaskManager | None = None

        logger.info("PeriodicCrawler initialized")

    async def __aenter__(self) -> "PeriodicCrawler":
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
        """Start the periodic crawler."""
        await self.core.start()
        await self._initialize_task_manager()
        logger.info("PeriodicCrawler started")

    async def stop(self) -> None:
        """Stop the periodic crawler."""
        if self._task_manager:
            await self._task_manager.stop()
        await self.core.stop()
        logger.info("PeriodicCrawler stopped")

    async def start_monitoring(self) -> None:
        """Start the background monitoring."""
        if not self._task_manager:
            logger.error("Task manager not initialized. Call start() first.")
            return

        await self._task_manager.start_periodic()
        logger.info("Background monitoring started")

    async def stop_monitoring(self) -> None:
        """Stop the background monitoring."""
        if not self._task_manager:
            logger.warning("Task manager not initialized")
            return

        await self._task_manager.stop_periodic()
        logger.info("Background monitoring stopped")

    async def get_status(self) -> PeriodicCrawlerStatus:
        """Get current crawler status and statistics.

        Returns:
            PeriodicCrawlerStatus with status information
        """
        core_status = await self.core.get_status()

        status = PeriodicCrawlerStatus(
            type="periodic",
            status="ready",
            core=core_status,
            config={
                "background_interval": self.config.background_interval,
                "recent_papers_limit": self.config.recent_papers_limit,
            },
        )

        # Add task manager status if available
        if self._task_manager:
            task_status = self._task_manager.get_status()
            # Convert dataclass to dict for compatibility
            status.monitoring = {
                "status": task_status.status,
                "periodic_running": task_status.periodic_running,
                "stats": task_status.stats,
                "config": task_status.config,
            }
            status.monitoring_active = task_status.periodic_running
        else:
            status.monitoring_active = False

        return status

    async def _initialize_task_manager(self) -> None:
        """Initialize the periodic task manager."""
        # Create monitoring task
        monitoring_task = RecentPapersMonitorTask(
            core=self.core,
            limit=self.config.recent_papers_limit,
        )

        # Create task manager
        self._task_manager = PeriodicTaskManager(
            task=monitoring_task,
            interval_seconds=self.config.background_interval,
            retry_delay=self.config.retry_delay,
            max_retries=self.config.max_retries,
            on_error=self.on_error,
        )

        await self._task_manager.start()

    async def _on_paper_crawled(self, paper: PaperEntity) -> None:
        """Internal callback when paper is crawled.

        Args:
            paper: The crawled paper
        """
        # Forward to external callback if provided
        if self.on_paper_crawled:
            await self.on_paper_crawled(paper)
