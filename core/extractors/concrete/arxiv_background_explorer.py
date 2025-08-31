"""ArXiv background explorer for continuous paper discovery."""

import asyncio
import re
from collections.abc import Callable
from typing import Any

from sqlalchemy.engine import Engine
from sqlmodel import Session, select

from core.log import get_logger
from core.models.domain.arxiv import ArxivPaper
from core.models.rows import ArxivCrawlProgress, ArxivFailedPaper, Paper
from core.types import PaperSummaryStatus
from core.utils import get_current_timestamp

logger = get_logger(__name__)


class ArxivBackgroundExplorer:
    """Background service for discovering and processing ArXiv papers."""

    def __init__(
        self,
        engine: Engine,
        categories: list[str],
        paper_interval_seconds: int = 2,
        fetch_interval_minutes: int = 10,
        retry_attempts: int = 3,
        retry_base_delay_seconds: float = 2.0,
    ) -> None:
        """Initialize the ArXiv background explorer.

        Args:
            engine: Database engine
            categories: List of ArXiv categories to explore
            paper_interval_seconds: Interval between processing individual papers
            fetch_interval_minutes: Interval between full fetch cycles in minutes
            retry_attempts: Number of retry attempts for failed papers
            retry_base_delay_seconds: Base delay for exponential backoff retries
        """
        self.engine = engine
        self.categories = categories
        self.paper_interval_seconds = paper_interval_seconds
        self.fetch_interval_minutes = fetch_interval_minutes
        self.retry_attempts = retry_attempts
        self.retry_base_delay_seconds = retry_base_delay_seconds

    def parse_arxiv_categories(self, categories_str: str) -> list[str]:
        """Parse and validate ArXiv categories from comma-separated string.

        Args:
            categories_str: Comma-separated string of ArXiv categories (e.g., "cs.AI,cs.LG")

        Returns:
            List of validated ArXiv categories

        Raises:
            ValueError: If any category has invalid format
        """
        if not categories_str or not categories_str.strip():
            raise ValueError("Categories string cannot be empty")

        categories = [cat.strip() for cat in categories_str.split(",") if cat.strip()]

        if not categories:
            raise ValueError("No valid categories found in string")

        arxiv_category_pattern = r"^[a-z-]+\.[A-Z][A-Za-z-]*$"

        for category in categories:
            if not re.match(arxiv_category_pattern, category):
                raise ValueError(f"Invalid ArXiv category format: {category}")

        logger.info(f"Parsed {len(categories)} ArXiv categories: {categories}")
        return categories

    async def load_crawl_progress(
        self, category: str, today_date: str
    ) -> tuple[str, int]:
        """Load crawl progress for a specific category.

        Args:
            category: ArXiv category (e.g., "cs.AI")
            today_date: Today's date in YYYY-MM-DD format

        Returns:
            Tuple of (last_crawled_date, last_crawled_index)
            If no progress exists, returns (today_date, 0)
        """
        with Session(self.engine) as session:
            progress = session.exec(
                select(ArxivCrawlProgress).where(
                    ArxivCrawlProgress.category == category
                )
            ).first()

            if progress is None:
                logger.info(
                    f"No progress found for category {category}, starting fresh"
                )
                return today_date, 0

            if progress.last_crawled_date != today_date:
                logger.info(
                    f"New day detected for {category}: "
                    f"last_crawled_date={progress.last_crawled_date}, "
                    f"today={today_date}, resetting index to 0"
                )
                return today_date, 0

            logger.info(
                f"Loaded progress for {category}: "
                f"date={progress.last_crawled_date}, "
                f"index={progress.last_crawled_index}"
            )
            return progress.last_crawled_date, progress.last_crawled_index

    async def save_crawl_progress(
        self, category: str, crawled_date: str, crawled_index: int
    ) -> None:
        """Save or update crawl progress for a specific category.

        Args:
            category: ArXiv category (e.g., "cs.AI")
            crawled_date: Date that was crawled (YYYY-MM-DD format)
            crawled_index: Index of the last processed paper
        """
        with Session(self.engine) as session:
            progress = session.exec(
                select(ArxivCrawlProgress).where(
                    ArxivCrawlProgress.category == category
                )
            ).first()

            if progress is None:
                progress = ArxivCrawlProgress(
                    category=category,
                    last_crawled_date=crawled_date,
                    last_crawled_index=crawled_index,
                    is_active=True,
                )
                session.add(progress)
                logger.info(
                    f"Created new progress for {category}: "
                    f"date={crawled_date}, index={crawled_index}"
                )
            else:
                progress.last_crawled_date = crawled_date
                progress.last_crawled_index = crawled_index
                logger.info(
                    f"Updated progress for {category}: "
                    f"date={crawled_date}, index={crawled_index}"
                )

            session.commit()

    async def store_paper_metadata(self, paper: ArxivPaper) -> "Paper":
        """Store paper metadata in the database with batched status.

        Args:
            paper: ArXivPaper object to store

        Returns:
            Created Paper object or existing Paper object if already exists
        """

        # Extract ArXiv-specific information from ArxivPaper
        arxiv_id = paper.arxiv_id
        primary_category = paper.primary_category
        all_categories = paper.categories

        with Session(self.engine) as session:
            # Check if paper already exists
            existing_paper = session.exec(
                select(Paper).where(Paper.arxiv_id == arxiv_id)
            ).first()

            if existing_paper is not None:
                logger.warning(
                    f"Paper with arxiv_id {arxiv_id} already exists, skipping"
                )
                return existing_paper

            # Create new paper record with batched status
            db_paper = Paper(
                arxiv_id=arxiv_id,
                title=paper.title,
                abstract=paper.abstract,
                primary_category=primary_category,
                categories=",".join(all_categories),
                authors=";".join(paper.authors),
                url_abs=paper.url_abs,
                url_pdf=paper.url_pdf,
                published_at=paper.published_date,
                summary_status=PaperSummaryStatus.BATCHED,
            )

            session.add(db_paper)
            session.commit()
            session.refresh(db_paper)

            logger.info(
                f"Stored paper metadata: {arxiv_id} "
                f"({paper.title[:50]}...) "
                f"with categories: {db_paper.categories}"
            )

            return db_paper

    async def handle_failed_paper(
        self, arxiv_id: str, category: str, error_message: str
    ) -> None:
        """Handle a failed paper by storing it in the failed papers table.

        Args:
            arxiv_id: ArXiv ID of the failed paper
            category: ArXiv category
            error_message: Error message describing the failure
        """

        with Session(self.engine) as session:
            # Check if this paper is already in the failed papers table
            existing_failed = session.exec(
                select(ArxivFailedPaper).where(ArxivFailedPaper.arxiv_id == arxiv_id)
            ).first()

            if existing_failed is not None:
                # Update existing failed paper record
                existing_failed.retry_count += 1
                existing_failed.last_retry_at = get_current_timestamp()
                existing_failed.error_message = error_message
                logger.info(
                    f"Updated failed paper {arxiv_id} (retry #{existing_failed.retry_count}): "
                    f"{error_message}"
                )
            else:
                # Create new failed paper record
                failed_paper = ArxivFailedPaper(
                    arxiv_id=arxiv_id,
                    category=category,
                    error_message=error_message,
                    retry_count=0,
                )
                session.add(failed_paper)
                logger.info(f"Stored failed paper {arxiv_id}: {error_message}")

            session.commit()

    async def retry_with_exponential_backoff(
        self,
        func: Callable[..., Any],
        *args: Any,
        max_retries: int | None = None,
        base_delay: float | None = None,
        **kwargs: Any,
    ) -> Any:
        """Retry a function with exponential backoff.

        Args:
            func: Function to retry
            *args: Arguments to pass to the function
            max_retries: Maximum number of retry attempts (uses instance default if None)
            base_delay: Base delay in seconds for exponential backoff (uses instance default if None)
            **kwargs: Keyword arguments to pass to the function

        Returns:
            Result of the function call

        Raises:
            Exception: The last exception raised by the function after all retries
        """
        import asyncio

        max_retries = max_retries if max_retries is not None else self.retry_attempts
        base_delay = (
            base_delay if base_delay is not None else self.retry_base_delay_seconds
        )

        last_exception: Exception | None = None

        for attempt in range(max_retries + 1):
            try:
                return await func(*args, **kwargs)
            except Exception as e:
                last_exception = e
                if attempt < max_retries:
                    delay = base_delay * (2**attempt)
                    logger.warning(
                        f"Attempt {attempt + 1} failed: {str(e)}. "
                        f"Retrying in {delay} seconds..."
                    )
                    await asyncio.sleep(delay)
                else:
                    logger.error(
                        f"All {max_retries + 1} attempts failed. "
                        f"Last error: {str(last_exception)}"
                    )

        if last_exception is not None:
            raise last_exception
        raise RuntimeError("No exception was captured during retries")

    async def process_single_paper(self, paper: ArxivPaper, category: str) -> bool:
        """Process a single paper by storing its metadata.

        Args:
            paper: ArXivPaper object with complete metadata
            category: ArXiv category

        Returns:
            True if processing succeeded, False if failed
        """
        try:
            # Store paper metadata directly (no need for additional API calls)
            await self.store_paper_metadata(paper)

            logger.info(f"Successfully processed paper {paper.arxiv_id}")
            return True

        except Exception as e:
            error_msg = f"Failed to process paper {paper.arxiv_id}: {str(e)}"
            logger.error(error_msg)
            await self.handle_failed_paper(paper.arxiv_id, category, error_msg)
            return False

    async def process_category_papers(
        self, category: str, today_date: str
    ) -> tuple[int, int]:
        """Process all papers for a specific category on a given date.

        Args:
            category: ArXiv category to process
            today_date: Date to process papers for (YYYY-MM-DD format)

        Returns:
            Tuple of (processed_count, failed_count)
        """
        from core.extractors.concrete.arxiv_source_explorer import ArxivSourceExplorer

        logger.info(f"Starting to process category {category} for date {today_date}")

        # Load progress for this category
        crawled_date, crawled_index = await self.load_crawl_progress(
            category, today_date
        )
        logger.info(f"Resuming from index {crawled_index} for category {category}")

        # Initialize the source explorer
        explorer = ArxivSourceExplorer()

        processed_count = 0
        failed_count = 0

        try:
            # Get papers for this category and date
            papers = await explorer.explore_new_papers_by_category(
                category, crawled_date, crawled_index, limit=100
            )

            if not papers:
                logger.info(
                    f"No papers found for category {category} on {crawled_date}"
                )
                return processed_count, failed_count

            # Process papers starting from the last crawled index
            for i, paper in enumerate(papers, start=crawled_index):
                # Process the paper with retry logic
                success = await self.retry_with_exponential_backoff(
                    self.process_single_paper, paper, category
                )

                if success:
                    processed_count += 1
                else:
                    failed_count += 1

                # Save progress after each paper
                await self.save_crawl_progress(category, crawled_date, i + 1)

                # Wait between papers (except for the last one)
                if i < len(papers) - 1:
                    await asyncio.sleep(self.paper_interval_seconds)

            logger.info(
                f"Completed processing category {category}: "
                f"{processed_count} processed, {failed_count} failed"
            )

        except Exception as e:
            logger.error(f"Error processing category {category}: {str(e)}")
            failed_count += 1

        return processed_count, failed_count

    async def run_background_service(self) -> None:
        """Run the background service that continuously processes ArXiv papers.

        This method runs indefinitely, processing papers for each category
        with configurable intervals between operations.
        """
        import asyncio
        from datetime import datetime, timedelta

        logger.info("Starting ArXiv background explorer service")
        logger.info(f"Processing categories: {', '.join(self.categories)}")

        while True:
            try:
                # Use yesterday's date for better chance of finding papers
                yesterday = (datetime.now() - timedelta(days=1)).strftime("%Y-%m-%d")
                today_date = yesterday  # Use yesterday instead of today
                total_processed = 0
                total_failed = 0

                # Process each category sequentially
                for category in self.categories:
                    logger.info(f"Processing category: {category}")

                    processed, failed = await self.process_category_papers(
                        category, today_date
                    )
                    total_processed += processed
                    total_failed += failed

                    logger.info(
                        f"Category {category} completed: "
                        f"{processed} processed, {failed} failed"
                    )

                logger.info(
                    f"Full cycle completed: {total_processed} total processed, "
                    f"{total_failed} total failed"
                )

                # Wait before starting the next cycle
                logger.info("Waiting before next fetch cycle...")
                await asyncio.sleep(self.fetch_interval_minutes * 60)

            except Exception as e:
                logger.error(f"Error in background service: {str(e)}")
                # Wait a bit before retrying
                await asyncio.sleep(60)
