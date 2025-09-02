"""ArXiv crawl manager for coordinating paper discovery and storage."""

import asyncio
from typing import Any

from core.log import get_logger

from .arxiv_source_explorer import ArxivSourceExplorer
from .arxiv_storage_manager import ArxivStorageManager

logger = get_logger(__name__)


class ArxivCrawlManager:
    """Manager for coordinating ArXiv paper crawling and storage."""

    def __init__(
        self,
        engine: Any,
        categories: list[str],
        delay_seconds: float = 2.0,
        max_results_per_request: int = 100,
    ) -> None:
        """Initialize the crawl manager.

        Args:
            engine: Database engine
            categories: List of ArXiv categories to crawl
            delay_seconds: Delay between requests in seconds
            max_results_per_request: Maximum results per API request
        """
        self.engine = engine
        self.categories = categories
        self.delay_seconds = delay_seconds
        self.max_results_per_request = max_results_per_request

        # Initialize storage manager only
        self.storage_manager = ArxivStorageManager(engine)

    async def crawl_and_store_papers(
        self,
        explorer: ArxivSourceExplorer,
        category: str,
        date: str,
        start_index: int = 0,
        limit: int = 100,
    ) -> tuple[int, int]:
        """Crawl papers for a specific category and date, then store them.

        Args:
            explorer: ArxivSourceExplorer instance for fetching papers
            category: ArXiv category (e.g., "cs.AI")
            date: Date in YYYY-MM-DD format
            start_index: Index to start fetching from
            limit: Maximum number of papers per request (default: 100)

        Returns:
            Tuple of (papers_found, papers_stored)
        """
        logger.info(f"Starting crawl for {category} on {date}")

        try:
            all_papers = []
            current_start = start_index
            batch_size = limit

            # Fetch all papers using pagination
            while True:
                logger.info(
                    f"Fetching batch starting from index {current_start} with limit {batch_size}"
                )

                batch = await explorer.explore_historical_papers_by_category(
                    category=category,
                    date=date,
                    start_index=current_start,
                    limit=batch_size,
                )

                if not batch:
                    logger.info(f"No more papers found at index {current_start}")
                    break

                all_papers.extend(batch)
                logger.info(
                    f"Fetched {len(batch)} papers in this batch, total so far: {len(all_papers)}"
                )

                # If we got fewer papers than requested, we've reached the end
                if len(batch) < batch_size:
                    logger.info(
                        f"Received {len(batch)} papers (less than {batch_size}), reached end of results"
                    )
                    break

                # Move to next batch
                current_start += batch_size

                # Rate limiting between batches
                if len(batch) == batch_size:  # Only if we expect more
                    await asyncio.sleep(self.delay_seconds)

            # Store all papers
            storage_manager = ArxivStorageManager(self.engine)
            papers_stored = await storage_manager.store_papers_batch(all_papers)

            logger.info(
                f"Found {len(all_papers)} papers, stored {papers_stored}/{len(all_papers)} papers for {category} on {date}"
            )

            return len(all_papers), papers_stored

        except Exception as e:
            logger.error(f"Error crawling {category} on {date}: {e}")
            return 0, 0

    async def crawl_category_range(
        self,
        explorer: ArxivSourceExplorer,
        category: str,
        start_date: str,
        end_date: str,
        papers_per_day: int = 100,
    ) -> dict[str, tuple[int, int]]:
        """Crawl papers for a category across a date range.

        Args:
            explorer: ArxivSourceExplorer instance for fetching papers
            category: ArXiv category to crawl
            start_date: Start date in YYYY-MM-DD format
            end_date: End date in YYYY-MM-DD format
            papers_per_day: Maximum papers to fetch per day

        Returns:
            Dictionary mapping dates to (papers_found, papers_stored) tuples
        """
        from datetime import datetime, timedelta

        start = datetime.strptime(start_date, "%Y-%m-%d")
        end = datetime.strptime(end_date, "%Y-%m-%d")

        results = {}
        current_date = start

        while current_date <= end:
            date_str = current_date.strftime("%Y-%m-%d")

            papers_found, papers_stored = await self.crawl_and_store_papers(
                explorer=explorer,
                category=category,
                date=date_str,
                start_index=0,
                limit=papers_per_day,
            )

            results[date_str] = (papers_found, papers_stored)
            current_date += timedelta(days=1)

        return results

    async def crawl_multiple_categories(
        self,
        explorer: ArxivSourceExplorer,
        categories: list[str],
        date: str,
        papers_per_category: int = 100,
    ) -> dict[str, tuple[int, int]]:
        """Crawl papers for multiple categories on a specific date.

        Args:
            explorer: ArxivSourceExplorer instance for fetching papers
            categories: List of ArXiv categories to crawl
            date: Date in YYYY-MM-DD format
            papers_per_category: Maximum papers to fetch per category

        Returns:
            Dictionary mapping categories to (papers_found, papers_stored) tuples
        """
        results = {}

        for category in categories:
            papers_found, papers_stored = await self.crawl_and_store_papers(
                explorer=explorer,
                category=category,
                date=date,
                start_index=0,
                limit=papers_per_category,
            )

            results[category] = (papers_found, papers_stored)

        return results
