"""Core ArXiv crawling functionality shared between on-demand and periodic crawlers."""

import asyncio
from dataclasses import dataclass
from datetime import datetime
from typing import Any, Awaitable, Callable

from core import AsyncRateLimiter, get_logger
from crawler.arxiv.client import ArxivClient
from crawler.arxiv.constants import (
    DEFAULT_MAX_RETRIES,
    DEFAULT_RATE_LIMIT,
    DEFAULT_RETRY_DELAY,
)
from crawler.arxiv.exceptions import ArxivNotFoundError
from crawler.arxiv.parser import ArxivParser
from crawler.database import (
    CrawlEvent,
    CrawlEventRepository,
    DatabaseManager,
    Paper,
    PaperRepository,
    SummaryRepository,
)

logger = get_logger(__name__)


@dataclass
class CrawlConfig:
    """Configuration for crawler behavior."""

    # Rate limiting
    requests_per_second: float = DEFAULT_RATE_LIMIT

    # Retry settings
    max_retries: int = DEFAULT_MAX_RETRIES
    retry_delay: int = DEFAULT_RETRY_DELAY

    # Database settings
    batch_size: int = 100


@dataclass
class CrawlStats:
    """Statistics for crawler operations."""

    papers_crawled: int = 0
    papers_failed: int = 0
    last_crawl_time: datetime | None = None
    start_time: datetime | None = None


@dataclass
class CrawlerStatus:
    """Status information for crawler."""

    stats: CrawlStats
    config: dict[str, Any]


class ArxivCrawlerCore:
    """Core ArXiv crawling functionality shared between crawler types."""

    def __init__(
        self,
        db_manager: DatabaseManager,
        config: CrawlConfig | None = None,
        on_paper_crawled: Callable[[Paper], Awaitable[None]] | None = None,
        on_error: Callable[[Exception], Awaitable[None]] | None = None,
    ):
        """Initialize the core crawler.

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

        # Repositories
        self.paper_repo: PaperRepository | None = None
        self.summary_repo: SummaryRepository | None = None
        self.event_repo: CrawlEventRepository | None = None

        # Rate limiter
        self.rate_limiter = AsyncRateLimiter(self.config.requests_per_second)

        # Parser
        self.parser = ArxivParser()

        # Statistics
        self.stats = CrawlStats()

        logger.info("ArxivCrawlerCore initialized")

    async def __aenter__(self) -> "ArxivCrawlerCore":
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
        """Start the core crawler and initialize components."""
        try:
            # Initialize database repositories
            await self._initialize_repositories()

            # Update statistics
            self.stats.start_time = datetime.now()

            logger.info("ArxivCrawlerCore started successfully")

        except Exception as e:
            logger.error(f"Failed to start core crawler: {e}")
            if self.on_error:
                await self.on_error(e)
            raise

    async def stop(self) -> None:
        """Stop the core crawler and cleanup resources."""
        logger.info("Stopping ArxivCrawlerCore...")
        logger.info("ArxivCrawlerCore stopped")

    async def crawl_single_paper(self, identifier: str) -> Paper | None:
        """Crawl a single paper by ID or URL.

        Args:
            identifier: arXiv ID, abstract URL, or PDF URL

        Returns:
            Crawled paper or None if failed
        """
        logger.info(f"Crawling single paper: {identifier}")

        try:
            # Record crawl event
            await self._record_crawl_event("FOUND", identifier)

            # Crawl the paper
            paper = await self._crawl_paper(identifier)

            if paper:
                self.stats.papers_crawled += 1
                if self.on_paper_crawled:
                    await self.on_paper_crawled(paper)
                logger.info(f"Successfully crawled paper: {paper.arxiv_id}")
            else:
                self.stats.papers_failed += 1
                logger.warning(f"Failed to crawl paper: {identifier}")

            return paper

        except Exception as e:
            self.stats.papers_failed += 1
            logger.error(f"Error crawling paper {identifier}: {e}")
            if self.on_error:
                await self.on_error(e)
            return None

    async def crawl_papers_batch(self, identifiers: list[str]) -> list[Paper]:
        """Crawl multiple papers in a batch.

        Args:
            identifiers: List of arXiv IDs, abstract URLs, or PDF URLs

        Returns:
            List of successfully crawled papers
        """
        logger.info(f"Crawling batch of {len(identifiers)} papers")

        crawled_papers = []

        # Use rate limiter for concurrent crawling
        async def crawl_with_rate_limit(identifier: str) -> Paper | None:
            await self.rate_limiter.wait()
            return await self.crawl_single_paper(identifier)

        # Crawl papers concurrently
        tasks = [crawl_with_rate_limit(identifier) for identifier in identifiers]
        results = await asyncio.gather(*tasks, return_exceptions=True)

        # Process results
        for i, result in enumerate(results):
            if isinstance(result, Exception):
                logger.error(f"Error crawling paper {identifiers[i]}: {result}")
                if self.on_error:
                    await self.on_error(result)
            elif isinstance(result, Paper):
                crawled_papers.append(result)

        logger.info(
            f"Successfully crawled {len(crawled_papers)} out of "
            f"{len(identifiers)} papers"
        )
        return crawled_papers

    async def get_status(self) -> CrawlerStatus:
        """Get current crawler status and statistics.

        Returns:
            CrawlerStatus with status information
        """
        return CrawlerStatus(
            stats=self.stats,
            config={
                "requests_per_second": self.config.requests_per_second,
                "max_retries": self.config.max_retries,
                "retry_delay": self.config.retry_delay,
            },
        )

    async def _initialize_repositories(self) -> None:
        """Initialize database repositories."""
        self.paper_repo = PaperRepository(self.db_manager)
        self.summary_repo = SummaryRepository(self.db_manager)
        self.event_repo = CrawlEventRepository(self.db_manager)

    async def _crawl_paper(self, identifier: str) -> Paper | None:
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
                    logger.warning(f"Failed to parse paper from XML: {identifier}")
                    return None

                # Check if paper already exists
                with self.db_manager:
                    if self.paper_repo is None:
                        raise RuntimeError("Paper repository not initialized")

                    existing_paper = self.paper_repo.get_by_arxiv_id(paper.arxiv_id)
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
                    stored_paper = self.paper_repo.get_by_arxiv_id(paper.arxiv_id)
                    return stored_paper

            except ArxivNotFoundError:
                logger.warning(f"Paper not found: {identifier}")
                return None
            except Exception as e:
                logger.error(f"Error crawling paper {identifier}: {e}")
                raise

    async def _record_crawl_event(self, event_type: str, identifier: str) -> None:
        """Record a crawl event in the database.

        Args:
            event_type: Type of crawl event
            identifier: Paper identifier or search criteria
        """
        try:
            event = CrawlEvent(
                arxiv_id=identifier if "." in identifier else None,
                event_type=event_type,
                detail=f"Identifier: {identifier}",
            )

            with self.db_manager:
                if self.event_repo is None:
                    raise RuntimeError("Event repository not initialized")
                self.event_repo.log_event(event)

        except Exception as e:
            logger.error(f"Failed to record crawl event: {e}")
