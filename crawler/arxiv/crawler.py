"""ArXiv crawler with background event loop and periodic fetching."""

import asyncio
import time
from datetime import datetime, timedelta
from enum import Enum
from typing import Optional, List, Dict, Any, Callable, Awaitable
from dataclasses import dataclass

from core import get_logger, AsyncRateLimiter
from crawler.arxiv.client import ArxivClient
from crawler.arxiv.parser import ArxivParser
from crawler.arxiv.constants import (
    DEFAULT_BACKGROUND_INTERVAL,
    DEFAULT_MAX_CONCURRENT_PAPERS,
    DEFAULT_RATE_LIMIT,
    DEFAULT_MAX_PAPERS_PER_BATCH,
    DEFAULT_MAX_RETRIES,
    DEFAULT_RETRY_DELAY,
    DEFAULT_BATCH_SIZE,
    DEFAULT_RECENT_PAPERS_LIMIT,
    DEFAULT_MONTHLY_PAPERS_LIMIT,
)
from crawler.arxiv.exceptions import ArxivError, ArxivNotFoundError
from crawler.database import (
    DatabaseManager,
    Paper,
    Summary,
    CrawlEvent,
    PaperRepository,
    SummaryRepository,
    CrawlEventRepository,
)

logger = get_logger(__name__)


class CrawlStatus(Enum):
    """Status of crawl operations."""

    IDLE = "idle"
    RUNNING = "running"
    PAUSED = "paused"
    STOPPED = "stopped"
    ERROR = "error"


class CrawlStrategy(Enum):
    """Crawl strategies for different paper sources."""

    SINGLE_PAPER = "single_paper"
    RECENT_PAPERS = "recent_papers"
    MONTHLY_PAPERS = "monthly_papers"
    YEARLY_PAPERS = "yearly_papers"


@dataclass
class CrawlConfig:
    """Configuration for crawler behavior."""

    # Background loop settings
    background_interval: int = DEFAULT_BACKGROUND_INTERVAL
    max_concurrent_papers: int = DEFAULT_MAX_CONCURRENT_PAPERS

    # Rate limiting
    requests_per_second: float = DEFAULT_RATE_LIMIT

    # Crawl limits
    max_papers_per_batch: int = DEFAULT_MAX_PAPERS_PER_BATCH
    max_retries: int = DEFAULT_MAX_RETRIES
    retry_delay: int = DEFAULT_RETRY_DELAY

    # Database settings
    batch_size: int = DEFAULT_BATCH_SIZE

    # Strategy-specific settings
    recent_papers_limit: int = DEFAULT_RECENT_PAPERS_LIMIT
    monthly_papers_limit: int = DEFAULT_MONTHLY_PAPERS_LIMIT


class ArxivCrawler:
    """ArXiv crawler with background event loop and periodic fetching."""

    def __init__(
        self,
        db_manager: DatabaseManager,
        config: Optional[CrawlConfig] = None,
        on_paper_crawled: Optional[Callable[[Paper], Awaitable[None]]] = None,
        on_error: Optional[Callable[[Exception], Awaitable[None]]] = None,
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
        self._background_task: Optional[asyncio.Task] = None
        self._stop_event = asyncio.Event()

        # Repositories
        self.paper_repo: Optional[PaperRepository] = None
        self.summary_repo: Optional[SummaryRepository] = None
        self.event_repo: Optional[CrawlEventRepository] = None

        # Rate limiter
        self.rate_limiter = AsyncRateLimiter(self.config.requests_per_second)

        # Parser
        self.parser = ArxivParser()

        # Statistics
        self.stats = {
            "papers_crawled": 0,
            "papers_failed": 0,
            "last_crawl_time": None,
            "start_time": None,
        }

        logger.info("ArXivCrawler initialized")

    async def __aenter__(self):
        """Async context manager entry."""
        await self.start()
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Async context manager exit."""
        await self.stop()

    async def start(self) -> None:
        """Start the crawler and initialize components."""
        if self.status != CrawlStatus.IDLE:
            logger.warning(f"Crawler already in {self.status} state")
            return

        try:
            # Initialize database repositories
            await self._initialize_repositories()

            # Reset stop event
            self._stop_event.clear()

            # Update status
            self.status = CrawlStatus.IDLE
            self.stats["start_time"] = datetime.now()

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

        # Signal background task to stop
        self._stop_event.set()

        # Cancel background task if running
        if self._background_task and not self._background_task.done():
            self._background_task.cancel()
            try:
                await self._background_task
            except asyncio.CancelledError:
                pass

        # Update status
        self.status = CrawlStatus.STOPPED
        logger.info("ArXivCrawler stopped")

    async def start_background_loop(self) -> None:
        """Start the background crawling loop."""
        if self.status == CrawlStatus.RUNNING:
            logger.warning("Background loop already running")
            return

        if self._background_task and not self._background_task.done():
            logger.warning("Background task already exists")
            return

        self.status = CrawlStatus.RUNNING
        self._background_task = asyncio.create_task(self._background_loop())
        logger.info("Background crawling loop started")

    async def stop_background_loop(self) -> None:
        """Stop the background crawling loop."""
        if self.status != CrawlStatus.RUNNING:
            logger.warning("Background loop not running")
            return

        self.status = CrawlStatus.PAUSED
        self._stop_event.set()

        if self._background_task:
            try:
                await self._background_task
            except asyncio.CancelledError:
                pass

        logger.info("Background crawling loop stopped")

    async def crawl_single_paper(self, identifier: str) -> Optional[Paper]:
        """Crawl a single paper by ID or URL.

        Args:
            identifier: arXiv ID, abstract URL, or PDF URL

        Returns:
            Crawled paper or None if failed
        """
        logger.info(f"Crawling single paper: {identifier}")

        try:
            # Record crawl event
            await self._record_crawl_event(
                CrawlStrategy.SINGLE_PAPER, identifier
            )

            # Crawl the paper
            paper = await self._crawl_paper(identifier)

            if paper:
                self.stats["papers_crawled"] += 1
                if self.on_paper_crawled:
                    await self.on_paper_crawled(paper)
                logger.info(f"Successfully crawled paper: {paper.arxiv_id}")
            else:
                self.stats["papers_failed"] += 1
                logger.warning(f"Failed to crawl paper: {identifier}")

            return paper

        except Exception as e:
            self.stats["papers_failed"] += 1
            logger.error(f"Error crawling paper {identifier}: {e}")
            if self.on_error:
                await self.on_error(e)
            return None

    async def crawl_recent_papers(
        self, limit: Optional[int] = None
    ) -> List[Paper]:
        """Crawl the most recent papers (placeholder for future implementation).

        Args:
            limit: Maximum number of papers to crawl

        Returns:
            List of crawled papers
        """
        limit = limit or self.config.recent_papers_limit
        logger.info(f"Crawling recent papers (limit: {limit})")

        # TODO: Implement recent papers crawling
        # This will use arXiv API to fetch recent papers in specific categories
        logger.warning("Recent papers crawling not yet implemented")
        return []

    async def crawl_monthly_papers(
        self, year: int, month: int, limit: Optional[int] = None
    ) -> List[Paper]:
        """Crawl papers from a specific month (placeholder for future implementation).

        Args:
            year: Year to crawl
            month: Month to crawl (1-12)
            limit: Maximum number of papers to crawl

        Returns:
            List of crawled papers
        """
        limit = limit or self.config.monthly_papers_limit
        logger.info(f"Crawling papers for {year}-{month:02d} (limit: {limit})")

        # TODO: Implement monthly papers crawling
        # This will use arXiv API to fetch papers from specific month
        logger.warning("Monthly papers crawling not yet implemented")
        return []

    async def get_status(self) -> Dict[str, Any]:
        """Get current crawler status and statistics.

        Returns:
            Dictionary with status information
        """
        return {
            "status": self.status.value,
            "background_task_running": self._background_task is not None
            and not self._background_task.done(),
            "stats": self.stats.copy(),
            "config": {
                "background_interval": self.config.background_interval,
                "max_concurrent_papers": self.config.max_concurrent_papers,
                "requests_per_second": self.config.requests_per_second,
            },
        }

    async def _initialize_repositories(self) -> None:
        """Initialize database repositories."""
        self.paper_repo = PaperRepository(self.db_manager)
        self.summary_repo = SummaryRepository(self.db_manager)
        self.event_repo = CrawlEventRepository(self.db_manager)

    async def _background_loop(self) -> None:
        """Background loop for periodic crawling."""
        logger.info("Background loop started")

        while not self._stop_event.is_set():
            try:
                logger.debug("Background loop iteration")

                # TODO: Implement periodic crawling logic
                # This will determine what papers to crawl based on strategy
                # For now, just log and wait

                # Wait for next iteration or stop signal
                try:
                    await asyncio.wait_for(
                        self._stop_event.wait(),
                        timeout=self.config.background_interval,
                    )
                except asyncio.TimeoutError:
                    # Timeout means continue with next iteration
                    pass

            except asyncio.CancelledError:
                logger.info("Background loop cancelled")
                break
            except Exception as e:
                logger.error(f"Error in background loop: {e}")
                if self.on_error:
                    await self.on_error(e)
                # Wait before retrying
                await asyncio.sleep(self.config.retry_delay)

        logger.info("Background loop stopped")

    async def _crawl_paper(self, identifier: str) -> Optional[Paper]:
        """Crawl a single paper and store in database.

        Args:
            identifier: arXiv ID, abstract URL, or PDF URL

        Returns:
            Crawled paper or None if failed
        """
        if not identifier or not identifier.strip():
            logger.warning("Empty identifier provided")
            return None
            
        async with ArxivClient() as client:
            try:
                # Fetch paper from arXiv API
                xml_response = await client.get_paper(identifier)

                # Parse XML response and extract paper metadata
                paper = self.parser.parse_paper(xml_response)
                if not paper:
                    logger.warning(
                        f"Failed to parse paper from XML: {identifier}"
                    )
                    return None

                # Check if paper already exists
                with self.db_manager:
                    existing_paper = self.paper_repo.get_by_arxiv_id(
                        paper.arxiv_id
                    )
                    if existing_paper:
                        logger.info(
                            f"Paper {paper.arxiv_id} already exists in database"
                        )
                        return existing_paper

                    # Store in database
                    paper_id = self.paper_repo.create(paper)
                    logger.info(
                        f"Stored paper {paper.arxiv_id} in database with ID {paper_id}"
                    )

                    # Retrieve the stored paper to return
                    stored_paper = self.paper_repo.get_by_arxiv_id(
                        paper.arxiv_id
                    )
                    return stored_paper

            except ArxivNotFoundError:
                logger.warning(f"Paper not found: {identifier}")
                return None
            except Exception as e:
                logger.error(f"Error crawling paper {identifier}: {e}")
                raise

    async def _record_crawl_event(
        self, strategy: CrawlStrategy, identifier: str
    ) -> None:
        """Record a crawl event in the database.

        Args:
            strategy: Crawl strategy used
            identifier: Paper identifier or search criteria
        """
        try:
            # Map strategy to valid event type
            event_type_map = {
                CrawlStrategy.SINGLE_PAPER: "FOUND",
                CrawlStrategy.RECENT_PAPERS: "FOUND",
                CrawlStrategy.MONTHLY_PAPERS: "FOUND",
                CrawlStrategy.YEARLY_PAPERS: "FOUND",
            }

            event = CrawlEvent(
                arxiv_id=identifier if "." in identifier else None,
                event_type=event_type_map.get(strategy, "FOUND"),
                detail=f"Strategy: {strategy.value}, Identifier: {identifier}",
            )

            with self.db_manager:
                self.event_repo.log_event(event)

        except Exception as e:
            logger.error(f"Failed to record crawl event: {e}")
