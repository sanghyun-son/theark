"""Historical ArXiv crawling manager for backward crawling from yesterday."""

import asyncio
from datetime import datetime, timedelta
from typing import Any, Sequence

from sqlmodel import Session, select
from sqlalchemy.engine import Engine

from core.extractors.concrete.arxiv_background_explorer import ArxivBackgroundExplorer
from core.log import get_logger
from core.models.rows import CategoryDateProgress, CrawlExecutionState
from core.utils import get_current_timestamp

logger = get_logger(__name__)


class HistoricalCrawlManager:
    """Manages historical ArXiv crawling from yesterday backwards."""

    def __init__(
        self, categories: Sequence[str], start_date: str | None = None
    ) -> None:
        """Initialize the historical crawl manager.

        Args:
            categories: List of ArXiv categories to crawl (e.g., ['cs.AI', 'cs.LG'])
            start_date: Start date in YYYY-MM-DD format (defaults to yesterday)
        """
        self.categories = list(categories)
        self.start_date = start_date or (datetime.now() - timedelta(days=1)).strftime(
            "%Y-%m-%d"
        )
        self.end_date = "2015-01-01"  # Hard limit as specified
        self.rate_limit_delay = 10  # 10 seconds between requests
        self.batch_size = 100  # Papers per request

        # Initialize background explorer (engine will be passed to methods)
        self.background_explorer = None

        logger.info(
            f"Historical crawl manager initialized with categories: {categories}"
        )
        logger.info(f"Start date: {self.start_date}, End date: {self.end_date}")

    def get_next_date_category(
        self, state: CrawlExecutionState
    ) -> tuple[str, str] | None:
        """Get the next date-category combination to process."""
        current_date = datetime.strptime(state.current_date, "%Y-%m-%d")
        end_date = datetime.strptime(self.end_date, "%Y-%m-%d")

        # Check if we've reached the end date
        if current_date < end_date:
            return None

        category = state.categories[state.current_category_index]
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
        self, engine: Engine, category: str, date: str
    ) -> tuple[int, int]:
        """Crawl papers for a specific date-category combination."""
        logger.info(f"Starting crawl for {category} on {date}")

        papers_found = 0
        papers_stored = 0

        try:
            # Create a temporary background explorer with the engine
            temp_explorer = ArxivBackgroundExplorer(
                engine=engine, categories=[category]
            )

            # Use background explorer to crawl papers
            papers = await temp_explorer.explore_papers_by_category_and_date(
                category=category, date=date, start_index=0, limit=self.batch_size
            )

            papers_found = len(papers)
            logger.info(f"Found {papers_found} papers for {category} on {date}")

            # Store papers
            for paper in papers:
                try:
                    stored_paper = await temp_explorer.store_paper_metadata(paper)
                    if stored_paper:
                        papers_stored += 1
                except Exception as e:
                    logger.warning(f"Failed to store paper {paper.arxiv_id}: {e}")

            # Rate limiting
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
        if state.current_category_index >= len(state.categories):
            state.current_category_index = 0
            current_date = datetime.strptime(state.current_date, "%Y-%m-%d")
            previous_date = current_date - timedelta(days=1)
            state.current_date = previous_date.strftime("%Y-%m-%d")

            # Check if we've reached the end date
            end_date = datetime.strptime(self.end_date, "%Y-%m-%d")
            if previous_date < end_date:
                logger.info(f"Reached end date {self.end_date}, crawling complete")
                state.is_active = False
                return False

        state.last_activity_at = get_current_timestamp()
        state.updated_at = get_current_timestamp()

        return True

    async def run_crawl_cycle(self, engine: Engine) -> None:
        """Run one crawl cycle."""
        with Session(engine) as db_session:
            # Get or initialize state within this session
            statement = select(CrawlExecutionState).limit(1)
            result = db_session.exec(statement)
            state = result.first()

            if not state:
                # Create new state
                state = CrawlExecutionState(
                    current_date=self.start_date,
                    current_category_index=0,
                    categories=self.categories,
                    is_active=True,
                    total_papers_found=0,
                    total_papers_stored=0,
                )
                db_session.add(state)
                db_session.commit()
                db_session.refresh(state)
                logger.info(f"Created new crawl state starting from {self.start_date}")
            else:
                # Update existing state if needed
                if state.categories != self.categories:
                    state.categories = self.categories
                    state.current_date = self.start_date
                    state.current_category_index = 0
                    state.total_papers_found = 0
                    state.total_papers_stored = 0
                    db_session.add(state)
                    db_session.commit()
                    logger.info("Updated existing crawl state with new categories")

            if not state.is_active:
                logger.info("Crawling is not active, skipping cycle")
                return

            # Get next date-category to process
            next_item = self.get_next_date_category(state)
            if not next_item:
                logger.info("No more date-category combinations to process")
                state.is_active = False
                db_session.add(state)
                db_session.commit()
                return

            date, category = next_item

            # Check if this date-category is already completed
            statement = select(CategoryDateProgress).where(
                CategoryDateProgress.category == category,
                CategoryDateProgress.date == date,
                CategoryDateProgress.is_completed,
            )
            result = db_session.exec(statement)
            if result.first():
                logger.info(
                    f"Date-category {category}-{date} already completed, skipping"
                )
                self.advance_to_next(state)
                return

            # Crawl the date-category
            try:
                papers_found, papers_stored = await self.crawl_date_category(
                    engine, category, date
                )

                # Update state totals
                state.total_papers_found += papers_found
                state.total_papers_stored += papers_stored
                db_session.add(state)
                db_session.commit()

                # Mark as completed
                await self.mark_date_category_completed(
                    engine, category, date, papers_found, papers_stored
                )

            except Exception as e:
                logger.error(f"Failed to crawl {category}-{date}: {e}")
                await self.mark_date_category_completed(
                    engine, category, date, 0, 0, str(e)
                )

            # Advance to next
            self.advance_to_next(state)

    async def run_continuous_crawl(self, engine: Engine) -> None:
        """Run continuous crawling until completion."""
        logger.info("Starting continuous historical crawl")

        while True:
            try:
                await self.run_crawl_cycle(engine)

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

    def get_progress_summary(self, engine: Engine) -> dict[str, Any]:
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

        total_papers_found = sum(p.papers_found for p in completed_count)
        total_papers_stored = sum(p.papers_stored for p in completed_count)

        return {
            "is_active": state.is_active if state else False,
            "current_date": state.current_date if state else None,
            "current_category": (
                state.categories[state.current_category_index] if state else None
            ),
            "categories": self.categories,
            "completed_date_categories": len(completed_count),
            "failed_date_categories": len(failed_count),
            "total_papers_found": total_papers_found,
            "total_papers_stored": total_papers_stored,
            "start_date": self.start_date,
            "end_date": self.end_date,
        }
