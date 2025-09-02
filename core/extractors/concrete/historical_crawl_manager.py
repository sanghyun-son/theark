"""Historical ArXiv crawling manager for backward crawling from yesterday."""

import asyncio
from collections.abc import Sequence
from datetime import datetime

from sqlalchemy.engine import Engine
from sqlmodel import Session, select

from core.extractors.concrete.arxiv_crawl_manager import ArxivCrawlManager
from core.extractors.concrete.arxiv_source_explorer import ArxivSourceExplorer
from core.log import get_logger
from core.models.api.responses import (
    CrawlCycleResult,
    CrawlerProgressResponse,
    CrawlerStatusResponse,
)
from core.models.rows import CrawlCompletion
from core.utils import (
    get_previous_date,
)

logger = get_logger(__name__)


class HistoricalCrawlManager:
    """Manages historical ArXiv crawling from yesterday backwards."""

    def __init__(
        self,
        categories: Sequence[str],
        rate_limit_delay: float = 10.0,
        batch_size: int = 100,
    ) -> None:
        """Initialize the historical crawl manager.

        Args:
            categories: List of ArXiv categories to crawl (e.g., ['cs.AI', 'cs.LG'])
            rate_limit_delay: Delay between requests in seconds (default: 10.0)
            batch_size: Number of papers per request (default: 100)
        """
        self.categories = list(categories)
        self.end_date = "2015-01-01"  # Hard limit as specified
        self.rate_limit_delay = rate_limit_delay
        self.batch_size = batch_size

        # Simple in-memory state
        self._current_date = get_previous_date(datetime.now().strftime("%Y-%m-%d"))
        self._current_category_index = 0
        self._completed_combinations: set[tuple[str, str]] = set()
        self._running = False
        self._crawl_task: asyncio.Task[None] | None = None

        logger.info(
            f"Historical crawl manager initialized with categories: {categories}"
        )
        logger.info(f"Will crawl from yesterday back to {self.end_date}")

    def get_next_date_category(self) -> tuple[str, str] | None:
        """Get the next date-category combination to process."""
        # Check if we've reached the end date
        if self._current_date <= self.end_date:
            logger.info(f"Reached end date {self.end_date}, crawling complete")
            return None

        # Get current category
        if self._current_category_index >= len(self.categories):
            return None

        category = self.categories[self._current_category_index]
        return self._current_date, category

    def advance_to_next(self) -> None:
        """Advance to the next date-category combination."""
        self._current_category_index += 1

        # If we've processed all categories for current date, move to previous date
        if self._current_category_index >= len(self.categories):
            self._current_category_index = 0
            self._current_date = get_previous_date(self._current_date)

    async def crawl_date_category(
        self, engine: Engine, explorer: ArxivSourceExplorer, category: str, date: str
    ) -> tuple[int, int]:
        """Crawl papers for a specific date-category combination."""
        try:
            # Create crawl manager for this operation
            crawl_manager = ArxivCrawlManager(
                engine=engine,
                categories=self.categories,
                delay_seconds=2.0,
                max_results_per_request=self.batch_size,
            )

            # Use crawl manager to crawl and store papers with injected explorer
            papers_found, papers_stored = await crawl_manager.crawl_and_store_papers(
                explorer=explorer,
                category=category,
                date=date,
                start_index=0,
                limit=self.batch_size,
            )

            # Mark as completed
            self._completed_combinations.add((category, date))
            self._save_completion_to_db(
                engine, category, date, papers_found, papers_stored
            )

            # Rate limiting
            await asyncio.sleep(self.rate_limit_delay)

            return papers_found, papers_stored

        except Exception as e:
            logger.error(f"Error crawling {category} on {date}: {e}")
            # Mark as completed even if failed
            self._completed_combinations.add((category, date))
            self._save_completion_to_db(engine, category, date, 0, 0)
            return 0, 0

    async def run_crawl_cycle(
        self, engine: Engine, explorer: ArxivSourceExplorer
    ) -> CrawlCycleResult | None:
        """Run one crawl cycle."""
        # Keep trying until we find an uncompleted date-category or reach the end
        while True:
            # Get next date-category to process
            next_item = self.get_next_date_category()
            if not next_item:
                logger.info("Reached end date, crawling complete")
                return None

            date, category = next_item

            # Check if already completed
            if (category, date) in self._completed_combinations:
                self.advance_to_next()
                continue  # Try next combination instead of returning None

            # Found uncompleted combination, execute crawl
            papers_found, papers_stored = await self.crawl_date_category(
                engine, explorer, category, date
            )

            # Advance to next
            self.advance_to_next()

            return CrawlCycleResult(
                papers_found=papers_found,
                papers_stored=papers_stored,
                category=category,
                date=date,
            )

    @property
    def current_date(self) -> str:
        """Get current date being processed."""
        return self._current_date

    @property
    def current_category_index(self) -> int:
        """Get current category index being processed."""
        return self._current_category_index

    def get_progress_summary(self, engine: Engine) -> CrawlerStatusResponse:
        """Get current crawling progress summary."""
        return CrawlerStatusResponse(
            is_running=self._running,
            is_active=self._running,
            current_date=self._current_date,
            current_category_index=self._current_category_index,
            categories=",".join(self.categories),
        )

    def get_progress_summary_for_progress(
        self, engine: Engine
    ) -> CrawlerProgressResponse:
        """Get current crawling progress summary for progress endpoint."""
        return CrawlerProgressResponse(
            total_papers_found=0,  # TODO: Implement actual counting
            total_papers_stored=0,  # TODO: Implement actual counting
            completed_date_categories=len(self._completed_combinations),
            failed_date_categories=0,  # TODO: Implement actual counting
        )

    async def start(self, explorer: ArxivSourceExplorer, engine: Engine) -> None:
        """Start the historical crawl manager with dependencies.

        Args:
            explorer: ArxivSourceExplorer instance for dependency injection
            engine: Database engine instance for persistence
        """
        if self._running:
            logger.warning("Historical crawl manager is already running")
            return

        logger.info("Starting historical crawl manager")
        self._running = True

        # Load completed combinations from database
        self._load_completed_combinations_from_db(engine)

        # Start background crawl task
        self._crawl_task = asyncio.create_task(self._crawl_scheduler(engine, explorer))

        logger.info("Historical crawl manager started successfully")

    def _load_completed_combinations_from_db(self, engine: Engine) -> None:
        """Load completed combinations from database."""
        try:
            with Session(engine) as session:
                completed_records = session.exec(
                    select(CrawlCompletion).where(
                        CrawlCompletion.category.in_(self.categories)  # type: ignore
                    )
                ).all()

                for record in completed_records:
                    self._completed_combinations.add((record.category, record.date))

        except Exception as e:
            logger.warning(f"Failed to load completed logs from DB: {e}")

        # Log completed combinations with smart truncation
        completed_count = len(self._completed_combinations)
        if completed_count == 0:
            logger.info("No completed logs found in DB")
            return

        completed_list = sorted(self._completed_combinations)
        if completed_count <= 4:
            combinations_str = ", ".join(
                [f"{cat}-{date}" for cat, date in completed_list]
            )
            logger.info(f"Loaded {completed_count} completed logs: {combinations_str}")
            return

        # Show first 2 and last 2 for readability
        first_two = ", ".join([f"{cat}-{date}" for cat, date in completed_list[:2]])
        last_two = ", ".join([f"{cat}-{date}" for cat, date in completed_list[-2:]])
        logger.info(
            f"Loaded {completed_count} completed logs: {first_two} ... {last_two}"
        )

    def _save_completion_to_db(
        self,
        engine: Engine,
        category: str,
        date: str,
        papers_found: int,
        papers_stored: int,
    ) -> None:
        """Save completion status to database."""
        try:
            with Session(engine) as session:
                completion = CrawlCompletion(
                    category=category,
                    date=date,
                    papers_found=papers_found,
                    papers_stored=papers_stored,
                )
                session.add(completion)
                session.commit()
        except Exception as e:
            logger.error(f"Failed to save completion status for {category}-{date}: {e}")
            return

        # Log DB save success (results already logged by arxiv_crawl_manager)
        logger.debug(f"Saved completion status for {category}-{date} to database")

    async def stop(self) -> None:
        """Stop the historical crawl manager."""
        if not self._running:
            logger.warning("Historical crawl manager is not running")
            return

        logger.info("Stopping historical crawl manager")
        self._running = False

        # Cancel and wait for crawl task
        if self._crawl_task:
            self._crawl_task.cancel()
            try:
                await self._crawl_task
            except asyncio.CancelledError:
                pass
            self._crawl_task = None

        logger.info("Historical crawl manager stopped successfully")

    async def _crawl_scheduler(
        self, engine: Engine, explorer: ArxivSourceExplorer
    ) -> None:
        """Background scheduler for historical crawling."""
        while self._running:
            try:
                # Run single crawl cycle
                result = await self.run_crawl_cycle(engine, explorer)
                if not result:
                    logger.info(
                        "Historical crawling completed - no more papers to process"
                    )
                    break

                # Wait before next cycle
                await asyncio.sleep(self.rate_limit_delay)

            except asyncio.CancelledError:
                logger.info("Historical crawl scheduler cancelled")
                break
            except Exception as e:
                logger.error(f"Error in historical crawl scheduler: {e}")
                await asyncio.sleep(self.rate_limit_delay)

    @property
    def is_running(self) -> bool:
        """Check if the crawl manager is running."""
        return self._running
