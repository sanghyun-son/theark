"""Historical ArXiv crawling manager for backward crawling from yesterday."""

import asyncio
from collections.abc import Sequence
from datetime import datetime, timedelta
from typing import Any

from sqlalchemy.engine import Engine
from sqlmodel import Session, select

from core.extractors.concrete.arxiv_crawl_manager import ArxivCrawlManager
from core.extractors.concrete.arxiv_source_explorer import ArxivSourceExplorer
from core.log import get_logger
from core.models.api.responses import CrawlCycleResult, CrawlExecutionStateResponse
from core.models.rows import CategoryDateProgress, CrawlExecutionState
from core.utils import (
    get_current_timestamp,
    get_previous_date,
    is_date_before_end,
    parse_categories_string,
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
        self.categories_str = ",".join(categories)
        self.end_date = "2015-01-01"  # Hard limit as specified
        self.rate_limit_delay = rate_limit_delay
        self.batch_size = batch_size
        self._running = False
        self._crawl_task: asyncio.Task[Any] | None = None

        logger.info(
            f"Historical crawl manager initialized with categories: {categories}"
        )
        logger.info(f"Will crawl from yesterday back to {self.end_date}")

    def get_next_date_category(
        self, state: CrawlExecutionState
    ) -> tuple[str, str | None] | None:
        """Get the next date-category combination to process."""
        # Always start from yesterday if current_date is not set or is in the past
        yesterday = (datetime.now() - timedelta(days=1)).strftime("%Y-%m-%d")

        if not state.current_date or is_date_before_end(state.current_date, yesterday):
            logger.info(f"Starting from recent date: {yesterday}")
            state.current_date = yesterday
            state.current_category_index = 0

        # Check if we've reached the end date
        if is_date_before_end(state.current_date, self.end_date):
            return None

        categories_list = parse_categories_string(state.categories)
        category = (
            categories_list[state.current_category_index]
            if state.current_category_index < len(categories_list)
            else None
        )
        return state.current_date, category

    async def mark_date_category_completed(
        self,
        engine: Engine,
        category: str,
        date: str,
        papers_found: int,
        papers_stored: int,
        error_message: str | None = None,
    ) -> None:
        """Mark a date-category combination as completed."""
        with Session(engine) as db_session:
            # Check if progress record exists
            statement = select(CategoryDateProgress).where(
                CategoryDateProgress.category == category,
                CategoryDateProgress.date == date,
            )
            result = db_session.exec(statement)
            progress = result.first()

            if not progress:
                progress = CategoryDateProgress(
                    category=category,
                    date=date,
                    started_at=get_current_timestamp(),
                )
                db_session.add(progress)

            # Update progress
            progress.is_completed = error_message is None
            progress.papers_found = papers_found
            progress.papers_stored = papers_stored
            progress.error_message = error_message
            progress.completed_at = get_current_timestamp()
            progress.updated_at = get_current_timestamp()

            db_session.add(progress)
            db_session.commit()

            status = "completed" if error_message is None else "failed"
            logger.info(
                f"Date-category {category}-{date} {status}: {papers_stored}/{papers_found} papers stored"
            )

    async def crawl_date_category(
        self, engine: Engine, explorer: ArxivSourceExplorer, category: str, date: str
    ) -> tuple[int, int]:
        """Crawl papers for a specific date-category combination."""
        logger.info(f"Starting crawl for {category} on {date}")

        papers_found = 0
        papers_stored = 0

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

            logger.info(
                f"Found {papers_found} papers, stored {papers_stored} papers for {category} on {date}"
            )

            # Rate limiting is handled by the crawl manager
            await asyncio.sleep(self.rate_limit_delay)

        except Exception as e:
            logger.error(f"Error crawling {category} on {date}: {e}")
            # Don't raise the exception, just return 0 papers found/stored
            # The error will be logged and the date-category will be marked as failed
            return 0, 0

        return papers_found, papers_stored

    def advance_to_next(self, state: CrawlExecutionState) -> bool:
        """Advance to the next date-category combination."""
        state.current_category_index += 1

        # If we've processed all categories for current date, move to previous date
        categories_list = parse_categories_string(state.categories)
        if state.current_category_index >= len(categories_list):
            state.current_category_index = 0
            state.current_date = get_previous_date(state.current_date)

            # Check if we've reached the end date
            if is_date_before_end(state.current_date, self.end_date):
                logger.info(f"Reached end date {self.end_date}, crawling complete")
                state.is_active = False
                return False

        state.last_activity_at = get_current_timestamp()
        state.updated_at = get_current_timestamp()

        return True

    def _initialize_or_update_state(self, db_session: Session) -> CrawlExecutionState:
        """Initialize or update crawl execution state."""
        statement = select(CrawlExecutionState).limit(1)
        result = db_session.exec(statement)
        state = result.first()

        if not state:
            # Create new state
            state = CrawlExecutionState(
                current_date=get_previous_date(datetime.now().strftime("%Y-%m-%d")),
                current_category_index=0,
                categories=self.categories_str,
                is_active=True,
                total_papers_found=0,
                total_papers_stored=0,
            )
            db_session.add(state)
            db_session.commit()
            db_session.refresh(state)
            logger.info(f"Created new crawl state starting from {state.current_date}")
        else:
            # Update existing state if needed
            if state.categories != self.categories_str:
                state.categories = self.categories_str
                state.current_date = get_previous_date(
                    datetime.now().strftime("%Y-%m-%d")
                )
                state.current_category_index = 0
                state.total_papers_found = 0
                state.total_papers_stored = 0
                db_session.add(state)
                db_session.commit()
                logger.info("Updated existing crawl state with new categories")

        return state

    def _is_date_category_completed(
        self, db_session: Session, category: str, date: str
    ) -> bool:
        """Check if date-category combination is already completed."""
        progress_statement = select(CategoryDateProgress).where(
            CategoryDateProgress.category == category,
            CategoryDateProgress.date == date,
            CategoryDateProgress.is_completed,
        )
        progress_result = db_session.exec(progress_statement)
        return progress_result.first() is not None

    def _should_skip_date_category(
        self, db_session: Session, category: str, date: str
    ) -> bool:
        """Determine if date-category should be skipped based on completion status."""
        # Always skip if already completed (simple approach)
        return self._is_date_category_completed(db_session, category, date)

    async def _execute_crawl_cycle(
        self, engine: Engine, explorer: ArxivSourceExplorer, state: CrawlExecutionState
    ) -> CrawlCycleResult | None:
        """Execute a single crawl cycle."""
        # Get next date-category to process
        next_item = self.get_next_date_category(state)
        if not next_item:
            logger.info("No more date-category combinations to process")
            state.is_active = False
            return None

        date, category = next_item

        if category is None:
            logger.warning(f"No category found for date {date}, skipping")
            return None

        with Session(engine) as db_session:
            if self._should_skip_date_category(db_session, category, date):
                logger.info(
                    f"Date-category {category}-{date} already completed, skipping"
                )
                self.advance_to_next(state)
                return None

        try:
            papers_found, papers_stored = await self.crawl_date_category(
                engine, explorer, category, date
            )

            # Update state totals
            state.total_papers_found += papers_found
            state.total_papers_stored += papers_stored

            # Mark as completed
            await self.mark_date_category_completed(
                engine, category, date, papers_found, papers_stored
            )

            # Advance to next
            self.advance_to_next(state)

            return CrawlCycleResult(
                papers_found=papers_found,
                papers_stored=papers_stored,
                category=category,
                date=date,
            )

        except Exception as e:
            logger.error(f"Failed to crawl {category}-{date}: {e}")
            await self.mark_date_category_completed(
                engine, category, date, 0, 0, str(e)
            )
            return None

    async def run_crawl_cycle(
        self, engine: Engine, explorer: ArxivSourceExplorer
    ) -> CrawlCycleResult | None:
        """Run one crawl cycle."""
        with Session(engine) as db_session:
            # Initialize or update state
            state = self._initialize_or_update_state(db_session)

            if not state.is_active:
                logger.info("Crawling is not active, skipping cycle")
                return None

            # Execute crawl cycle
            result = await self._execute_crawl_cycle(engine, explorer, state)

            # Save state changes
            db_session.add(state)
            db_session.commit()

            return result

    async def run_continuous_crawl(
        self, engine: Engine, explorer: ArxivSourceExplorer
    ) -> None:
        """Run continuous crawling until completion."""
        logger.info("Starting continuous historical crawl")

        while True:
            try:
                await self.run_crawl_cycle(engine, explorer)

                # Check if crawling is complete
                with Session(engine) as db_session:
                    state = db_session.exec(
                        select(CrawlExecutionState).limit(1)
                    ).first()
                    if state and not state.is_active:
                        logger.info("Historical crawling completed")
                        break

                # Rate limiting between cycles
                await asyncio.sleep(self.rate_limit_delay)

            except Exception as e:
                logger.error(f"Error in crawl cycle: {e}")
                await asyncio.sleep(60)  # Wait 1 minute before retrying
                return None

    def get_progress_summary(self, engine: Engine) -> CrawlExecutionStateResponse:
        """Get a summary of crawling progress."""
        with Session(engine) as db_session:
            # Get execution state
            state = db_session.exec(select(CrawlExecutionState).limit(1)).first()

            # Get progress statistics
            completed_count = db_session.exec(
                select(CategoryDateProgress).where(CategoryDateProgress.is_completed)
            ).all()

            # Get all progress records and filter in Python
            all_progress = db_session.exec(select(CategoryDateProgress)).all()
            failed_count = [p for p in all_progress if not p.is_completed]

        return CrawlExecutionStateResponse.from_crawl_state(
            crawl_state=state,
            start_date=get_previous_date(datetime.now().strftime("%Y-%m-%d")),
            end_date=self.end_date,
            completed_count=len(completed_count),
            failed_count=len(failed_count),
        )

    async def start(self, explorer: ArxivSourceExplorer, engine: Engine) -> None:
        """Start the historical crawl manager with dependencies.

        Args:
            explorer: ArxivSourceExplorer instance for dependency injection
            engine: Database engine instance
        """
        if self._running:
            logger.warning("Historical crawl manager is already running")
            return

        logger.info("Starting historical crawl manager")
        self._running = True

        # Start background crawl task
        self._crawl_task = asyncio.create_task(self._crawl_scheduler(engine, explorer))

        logger.info("Historical crawl manager started successfully")

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
                    logger.info("No more papers to crawl, stopping scheduler")
                    break

                # Wait before next cycle
                await asyncio.sleep(self.rate_limit_delay)

            except asyncio.CancelledError:
                logger.info("Crawl scheduler cancelled")
                break
            except Exception as e:
                logger.error(f"Error in crawl scheduler: {e}")
                await asyncio.sleep(self.rate_limit_delay)

    @property
    def is_running(self) -> bool:
        """Check if the crawl manager is running."""
        return self._running
