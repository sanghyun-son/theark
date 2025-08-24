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
    interest_section: str = ""


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
        arxiv_client: ArxivClient | None = None,
    ):
        """Initialize the core crawler.

        Args:
            config: Crawler configuration
            on_paper_crawled: Callback when paper is successfully crawled
            on_error: Callback when error occurs
            arxiv_client: Optional ArxivClient instance for dependency injection
        """
        self.config = config or CrawlConfig()
        self.on_paper_crawled = on_paper_crawled
        self.on_error = on_error
        self.arxiv_client = arxiv_client

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
        self, identifier: str, db_manager: DatabaseManager
    ) -> PaperEntity | None:
        """Crawl a single paper by ID or URL.

        Args:
            identifier: arXiv ID, abstract URL, or PDF URL
            db_manager: Database manager instance

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
            paper = await self._crawl_paper(identifier, db_manager, paper_repo)

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
        self, identifiers: list[str], db_manager: DatabaseManager
    ) -> list[PaperEntity]:
        """Crawl multiple papers in a batch.

        Args:
            identifiers: List of arXiv IDs, abstract URLs, or PDF URLs
            db_manager: Database manager instance

        Returns:
            List of successfully crawled papers
        """
        logger.info(f"Crawling batch of {len(identifiers)} papers")

        crawled_papers = []

        # Use rate limiter for concurrent crawling
        async def crawl_with_rate_limit(identifier: str) -> PaperEntity | None:
            await self.rate_limiter.wait()
            return await self.crawl_single_paper(identifier, db_manager)

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
                from core.config import settings

                return SummarizationService(
                    base_url=settings.llm_api_base_url,
                    use_tools=self.config.summarization.use_tools,
                    model=self.config.summarization.model,
                    db_manager=llm_db_manager,
                )
            except Exception as e:
                logger.error(f"Failed to create summarization service: {e}")
                return None
        return None

    async def _crawl_paper(
        self, identifier: str, db_manager: DatabaseManager, paper_repo: PaperRepository
    ) -> PaperEntity | None:
        """Crawl a single paper and store in database.

        Args:
            identifier: arXiv ID, abstract URL, or PDF URL
            db_manager: Database manager instance
            paper_repo: Paper repository instance

        Returns:
            Crawled paper or None if failed
        """
        if not identifier or not identifier.strip():
            logger.warning("Empty identifier provided")
            return None

        # Use injected client or create a new one
        if self.arxiv_client:
            # Use injected client (already managed externally)
            return await self._crawl_with_client(
                self.arxiv_client, identifier, db_manager, paper_repo
            )
        else:
            # Create new client with settings
            from core.config import settings

            base_url = f"{settings.arxiv_api_base_url}/api/query"
            client = ArxivClient(base_url=base_url)
            return await self._crawl_with_client(
                client, identifier, db_manager, paper_repo
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

    async def _summarize_paper(
        self, paper: PaperEntity, llm_db_manager: Any, summary_repo: SummaryRepository
    ) -> None:
        """Summarize a paper and store the summary in the database.

        Args:
            paper: The paper to summarize
            llm_db_manager: LLM database manager instance
            summary_repo: Summary repository instance
        """
        if not self.config.summarization:
            return

        # Get summarization service
        summarization_service = self._get_summarization_service(llm_db_manager)
        if not summarization_service:
            return

        try:
            # Get the abstract text
            abstract = paper.abstract or ""
            if not abstract.strip():
                logger.warning(f"No abstract available for paper {paper.arxiv_id}")
                return

            # Summarize the paper
            summary_response = await summarization_service.summarize_paper(
                paper_id=paper.arxiv_id,
                abstract=abstract,
                language=self.config.summarization.language,
                interest_section=self.config.summarization.interest_section,
            )

            if summary_response:
                # Check if we have a valid paper_id before creating summary
                if not paper.paper_id or paper.paper_id <= 0:
                    logger.warning(
                        f"Cannot create summary for paper {paper.arxiv_id}: "
                        f"invalid paper_id {paper.paper_id}"
                    )
                    return

                # Create summary record
                from core.models.database.entities import SummaryEntity

                # Convert relevance string to integer score
                relevance_map = {
                    "Must": 10,
                    "High": 8,
                    "Medium": 5,
                    "Low": 2,
                    "Irrelevant": 0,
                }

                # Get relevance value
                relevance_value = (
                    summary_response.structured_summary.relevance
                    if summary_response.structured_summary
                    else "Medium"
                )

                # Handle both string and numeric relevance values
                if relevance_value.isdigit():
                    relevance_score = int(relevance_value)
                else:
                    relevance_score = relevance_map.get(relevance_value, 5)

                # Create overview from structured summary
                if summary_response.structured_summary:
                    overview = summary_response.structured_summary.tldr
                    motivation = summary_response.structured_summary.motivation
                    method = summary_response.structured_summary.method
                    result = summary_response.structured_summary.result
                    conclusion = summary_response.structured_summary.conclusion
                else:
                    overview = summary_response.summary or ""
                    motivation = "Not available"
                    method = "Not available"
                    result = "Not available"
                    conclusion = "Not available"

                summary = SummaryEntity(
                    paper_id=paper.paper_id,
                    version=1,
                    overview=overview,
                    motivation=motivation,
                    method=method,
                    result=result,
                    conclusion=conclusion,
                    language=self.config.summarization.language,
                    interests=self.config.summarization.interest_section,
                    relevance=relevance_score,
                    model=(
                        summary_response.metadata.get("model")
                        if summary_response.metadata
                        else None
                    ),
                )

                summary_id = summary_repo.create(summary)
                logger.info(
                    f"Stored summary for paper {paper.arxiv_id} "
                    f"with ID {summary_id}"
                )

        except Exception as e:
            logger.error(f"Failed to summarize paper {paper.arxiv_id}: {e}")
            # Don't fail the entire crawling process if summarization fails
