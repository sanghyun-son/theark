"""Core ArXiv crawling functionality shared between on-demand and periodic crawlers."""

import asyncio
from dataclasses import dataclass
from datetime import datetime
from typing import Any, Awaitable, Callable

from core import AsyncRateLimiter, get_logger
from core.models.database.entities import PaperEntity
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
    PaperRepository,
    SummaryRepository,
)
from crawler.summarizer.service import SummarizationService

logger = get_logger(__name__)


@dataclass
class SummarizationConfig:
    """Configuration for summarization behavior."""

    # Whether to summarize papers immediately after crawling
    summarize_immediately: bool = False

    # Whether to use structured output (function calling)
    use_tools: bool = True

    # OpenAI model to use
    model: str = "gpt-4o-mini"

    # Language for summaries
    language: str = "English"

    # User interest section for relevance scoring
    interest_section: str = "Machine Learning,Deep Learning"


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

    # Summarization settings
    summarization: SummarizationConfig | None = None


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
        config: CrawlConfig | None = None,
        on_paper_crawled: Callable[[PaperEntity], Awaitable[None]] | None = None,
        on_error: Callable[[Exception], Awaitable[None]] | None = None,
    ):
        """Initialize the core crawler.

        Args:
            config: Crawler configuration
            on_paper_crawled: Callback when paper is successfully crawled
            on_error: Callback when error occurs
        """
        self.config = config or CrawlConfig()
        self.on_paper_crawled = on_paper_crawled
        self.on_error = on_error

        self.rate_limiter = AsyncRateLimiter(self.config.requests_per_second)
        self.parser = ArxivParser()
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

    async def crawl_single_paper(
        self, identifier: str, db_manager: DatabaseManager, arxiv_client: ArxivClient
    ) -> PaperEntity | None:
        """Crawl a single paper by ID or URL.

        Args:
            identifier: arXiv ID, abstract URL, or PDF URL
            db_manager: Database manager instance
            arxiv_client: ArxivClient instance for dependency injection

        Returns:
            Crawled paper or None if failed
        """
        logger.info(f"Crawling single paper: {identifier}")

        try:
            # Get repositories
            paper_repo, summary_repo, event_repo = self._get_repositories(db_manager)

            # Record crawl event
            await self._record_crawl_event("FOUND", identifier, event_repo)

            # Crawl the paper
            paper = await self._crawl_paper(
                identifier, db_manager, paper_repo, arxiv_client
            )

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

    async def crawl_papers_batch(
        self,
        identifiers: list[str],
        db_manager: DatabaseManager,
        arxiv_client: ArxivClient,
    ) -> list[PaperEntity]:
        """Crawl multiple papers in a batch.

        Args:
            identifiers: List of arXiv IDs, abstract URLs, or PDF URLs
            db_manager: Database manager instance
            arxiv_client: ArxivClient instance for dependency injection

        Returns:
            List of successfully crawled papers
        """
        logger.info(f"Crawling batch of {len(identifiers)} papers")

        crawled_papers = []

        # Use rate limiter for concurrent crawling
        async def crawl_with_rate_limit(identifier: str) -> PaperEntity | None:
            await self.rate_limiter.wait()
            return await self.crawl_single_paper(identifier, db_manager, arxiv_client)

        # Crawl papers concurrently
        tasks = [crawl_with_rate_limit(identifier) for identifier in identifiers]
        results = await asyncio.gather(*tasks, return_exceptions=True)

        # Process results
        for i, result in enumerate(results):
            if isinstance(result, Exception):
                logger.error(f"Error crawling paper {identifiers[i]}: {result}")
                if self.on_error:
                    await self.on_error(result)
            elif isinstance(result, PaperEntity):
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

    def _get_repositories(
        self, db_manager: DatabaseManager
    ) -> tuple[PaperRepository, SummaryRepository, CrawlEventRepository]:
        """Get database repositories.

        Args:
            db_manager: Database manager instance

        Returns:
            Tuple of (paper_repo, summary_repo, event_repo)
        """
        paper_repo = PaperRepository(db_manager)
        summary_repo = SummaryRepository(db_manager)
        event_repo = CrawlEventRepository(db_manager)
        return paper_repo, summary_repo, event_repo

    def _get_summarization_service(
        self, llm_db_manager: Any
    ) -> SummarizationService | None:
        """Get summarization service if configured.

        Args:
            llm_db_manager: LLM database manager instance

        Returns:
            SummarizationService instance or None if not configured
        """
        if (
            self.config.summarization
            and self.config.summarization.summarize_immediately
        ):
            try:
                return SummarizationService()
            except Exception as e:
                logger.error(f"Failed to create summarization service: {e}")
                return None
        return None

    async def _crawl_paper(
        self,
        identifier: str,
        db_manager: DatabaseManager,
        paper_repo: PaperRepository,
        arxiv_client: ArxivClient,
    ) -> PaperEntity | None:
        """Crawl a single paper and store in database.

        Args:
            identifier: arXiv ID, abstract URL, or PDF URL
            db_manager: Database manager instance
            paper_repo: Paper repository instance
            arxiv_client: ArxivClient instance for dependency injection

        Returns:
            Crawled paper or None if failed
        """
        if not identifier or not identifier.strip():
            logger.warning("Empty identifier provided")
            return None

        # Use injected client
        return await self._crawl_with_client(
            arxiv_client, identifier, db_manager, paper_repo
        )

    async def _crawl_with_client(
        self,
        client: ArxivClient,
        identifier: str,
        db_manager: DatabaseManager,
        paper_repo: PaperRepository,
    ) -> PaperEntity | None:
        """Crawl paper using the provided client."""
        try:
            # Fetch paper from arXiv API
            xml_response = await client.get_paper(identifier)

            # Parse XML response and extract paper metadata
            paper = self.parser.parse_paper(xml_response)
            if not paper:
                logger.warning(f"Failed to parse paper from XML: {identifier}")
                return None

            # Check if paper already exists
            existing_paper = paper_repo.get_by_arxiv_id(paper.arxiv_id)
            if existing_paper:
                logger.info(f"Paper {paper.arxiv_id} already exists in database")
                return existing_paper

            # Store in database
            paper_id = paper_repo.create(paper)
            logger.info(f"Stored paper {paper.arxiv_id} in database with ID {paper_id}")

            # Retrieve the stored paper to get the database ID
            stored_paper = paper_repo.get_by_arxiv_id(paper.arxiv_id)

            return stored_paper

        except ArxivNotFoundError:
            logger.warning(f"Paper not found: {identifier}")
            return None
        except Exception as e:
            logger.error(f"Error crawling paper {identifier}: {e}")
            raise

    async def _record_crawl_event(
        self, event_type: str, identifier: str, event_repo: CrawlEventRepository
    ) -> None:
        """Record a crawl event in the database.

        Args:
            event_type: Type of crawl event
            identifier: Paper identifier or search criteria
            event_repo: Event repository instance
        """
        try:
            event = CrawlEvent(
                arxiv_id=identifier if "." in identifier else None,
                event_type=event_type,
                detail=f"Identifier: {identifier}",
            )

            event_repo.log_event(event)

        except Exception as e:
            logger.error(f"Failed to record crawl event: {e}")
