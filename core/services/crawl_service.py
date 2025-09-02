"""Service for managing crawling operations."""

from sqlalchemy.engine import Engine

from core.extractors.concrete.arxiv_source_explorer import ArxivSourceExplorer
from core.extractors.concrete.historical_crawl_manager import HistoricalCrawlManager
from core.log import get_logger
from core.models.api.responses import (
    CrawlerProgressResponse,
    CrawlerStatusResponse,
)

logger = get_logger(__name__)


class CrawlService:
    """Stateless service for managing crawling operations."""

    def __init__(self, crawl_manager: HistoricalCrawlManager) -> None:
        """Initialize crawl service."""
        self.crawl_manager = crawl_manager

    def is_running(self, engine: Engine) -> bool:
        """Check if crawling is currently running."""
        return self.crawl_manager.is_running

    async def start_crawling(
        self, explorer: ArxivSourceExplorer, engine: Engine
    ) -> bool:
        """Start crawling operation."""
        if self.is_running(engine):
            logger.info("Crawling is already running")
            return False

        try:
            logger.info("Starting crawling operation")
            await self.crawl_manager.start(explorer, engine)
            return True
        except Exception as e:
            logger.error(f"Failed to start crawling: {e}")
            return False

    async def stop_crawling(self) -> bool:
        """Stop crawling operation."""
        try:
            logger.info("Stopping crawling operation")
            await self.crawl_manager.stop()
            return True
        except Exception as e:
            logger.error(f"Failed to stop crawling: {e}")
            return False

    def get_status(self, engine: Engine) -> CrawlerStatusResponse:
        """Get current crawling status."""
        return self.crawl_manager.get_progress_summary(engine)

    def get_progress(self, engine: Engine) -> CrawlerProgressResponse:
        """Get current crawling progress."""
        return self.crawl_manager.get_progress_summary_for_progress(engine)
