#!/usr/bin/env python3
"""Comprehensive demo script for TheArk - ArXiv Paper Discovery and Summarization System."""

import asyncio
from datetime import datetime, timedelta
from pathlib import Path

from core.log import setup_logging, get_logger
from core.database.engine import create_database_engine, create_database_tables
from core.extractors.concrete.arxiv_background_explorer import ArxivBackgroundExplorer
from core.models.rows import CrawlExecutionState
from core.types import Environment
from sqlmodel import Session, select

# Set up logging
setup_logging(level="INFO", use_colors=True)
logger = get_logger(__name__)


class TheArkDemo:
    """Comprehensive demo for TheArk system."""

    def __init__(self):
        """Initialize the demo."""
        self.demo_db_path = Path("db/theark.demo.db")
        self.engine = None
        self.background_explorer = None

    async def setup_database(self):
        """Set up the demo database."""
        logger.info("=== Setting up Demo Database ===")
        logger.info(f"Database path: {self.demo_db_path}")

        # Create database engine with demo path
        self.engine = create_database_engine(
            environment=Environment.DEVELOPMENT, db_path=self.demo_db_path
        )

        # Create database tables
        create_database_tables(self.engine)
        logger.info("✅ Database setup completed")

    async def test_crawl_execution_state(self):
        """Test CrawlExecutionState functionality."""
        logger.info("\n=== Testing CrawlExecutionState ===")

        with Session(self.engine) as session:
            # Check if state already exists
            existing_state = session.exec(select(CrawlExecutionState)).first()

            if existing_state:
                logger.info(f"Found existing state: {existing_state}")
                state = existing_state
            else:
                # Create new state
                today = datetime.now().strftime("%Y-%m-%d")
                yesterday = (datetime.now() - timedelta(days=1)).strftime("%Y-%m-%d")

                state = CrawlExecutionState(
                    last_execution_date=today,
                    historical_crawl_date=yesterday,
                    historical_crawl_index=0,
                    today_crawler_active=True,
                    historical_crawler_active=True,
                )
                session.add(state)
                session.commit()
                session.refresh(state)
                logger.info(f"Created new state: {state}")

            # Test state updates
            state.historical_crawl_index = 10
            state.historical_crawl_date = "2025-08-15"
            state.updated_at = datetime.now().isoformat()
            session.commit()
            session.refresh(state)
            logger.info(f"Updated state: {state}")

        logger.info("✅ CrawlExecutionState tests completed")

    async def test_category_parsing(self):
        """Test category parsing functionality."""
        logger.info("\n=== Testing Category Parsing ===")

        if not self.engine:
            logger.error("Database engine not initialized")
            return

        # Initialize background explorer for category parsing
        self.background_explorer = ArxivBackgroundExplorer(
            engine=self.engine, categories=["cs.AI", "cs.LG", "cs.CL"]
        )

        # Test valid categories string parsing
        valid_categories = "cs.AI,cs.LG,cs.CL"
        parsed = self.background_explorer.parse_arxiv_categories(valid_categories)
        logger.info(f"Parsed categories from string: {parsed}")

        # Test invalid category
        try:
            self.background_explorer.parse_arxiv_categories("invalid.category")
        except ValueError as e:
            logger.info(f"Correctly caught invalid category: {e}")

        # Show current categories
        logger.info(
            f"Current explorer categories: {self.background_explorer.categories}"
        )

        logger.info("✅ Category parsing tests completed")

    async def test_progress_tracking(self):
        """Test progress tracking functionality."""
        logger.info("\n=== Testing Progress Tracking ===")

        if not self.engine:
            logger.error("Database engine not initialized")
            return

        # Use the same background explorer instance
        if not hasattr(self, "background_explorer") or self.background_explorer is None:
            self.background_explorer = ArxivBackgroundExplorer(
                engine=self.engine, categories=["cs.AI", "cs.LG", "cs.CL"]
            )

        # Test progress saving and loading
        await self.background_explorer.save_crawl_progress("cs.AI", "2024-01-15", 5)
        crawled_date, crawled_index = (
            await self.background_explorer.load_crawl_progress("cs.AI", "2024-01-15")
        )
        logger.info(
            f"Progress tracking works: date={crawled_date}, index={crawled_index}"
        )

        # Test new day detection
        new_day_date, new_day_index = (
            await self.background_explorer.load_crawl_progress("cs.AI", "2024-01-16")
        )
        logger.info(f"New day progress: date={new_day_date}, index={new_day_index}")

        logger.info("✅ Progress tracking tests completed")

    async def test_paper_crawling(self):
        """Test actual paper crawling functionality."""
        logger.info("\n=== Testing Paper Crawling ===")
        logger.info("This will crawl actual papers from ArXiv (may take a moment)...")

        if not self.engine:
            logger.error("Database engine not initialized")
            return

        # Use the same background explorer instance
        if not hasattr(self, "background_explorer") or self.background_explorer is None:
            self.background_explorer = ArxivBackgroundExplorer(
                engine=self.engine, categories=["cs.AI", "cs.LG", "cs.CL"]
            )

        logger.info(f"Processing categories: {self.background_explorer.categories}")

        # Try multiple dates to find papers
        test_dates = [
            (datetime.now() - timedelta(days=1)).strftime("%Y-%m-%d"),  # Yesterday
            (datetime.now() - timedelta(days=3)).strftime("%Y-%m-%d"),  # 3 days ago
            (datetime.now() - timedelta(days=7)).strftime("%Y-%m-%d"),  # 1 week ago
        ]

        total_processed = 0
        total_failed = 0

        for test_date in test_dates:
            logger.info(f"Trying date: {test_date}")

            # Process all categories
            for category in self.background_explorer.categories:
                logger.info(f"Processing {category} category...")
                processed, failed = (
                    await self.background_explorer.process_category_papers(
                        category, test_date
                    )
                )
                logger.info(
                    f"{category} result: {processed} processed, {failed} failed"
                )

                total_processed += processed
                total_failed += failed

            # If we found some papers, we can stop
            if total_processed > 0:
                logger.info(f"Found papers! Stopping at date: {test_date}")
                break

        logger.info(f"Total papers processed: {total_processed}")
        logger.info(f"Total papers failed: {total_failed}")

        if total_processed == 0:
            logger.warning("No papers found in any of the tested dates")
            logger.info(
                "This is normal - ArXiv may not have papers for these specific dates"
            )

        logger.info("✅ Paper crawling tests completed")

    async def show_database_info(self):
        """Show database information."""
        logger.info("\n=== Database Information ===")
        logger.info(f"Database path: {self.demo_db_path}")

        if not self.engine:
            logger.error("Database engine not initialized")
            return

        if self.demo_db_path.exists():
            size = self.demo_db_path.stat().st_size
            logger.info(f"Database size: {size} bytes")

            # Get database stats
            with Session(self.engine) as session:
                # Count papers
                from core.models.rows import Paper

                paper_count = session.exec(select(Paper)).all()
                logger.info(f"Papers in database: {len(paper_count)}")

                # Count summaries
                from core.models.rows import Summary

                summary_count = session.exec(select(Summary)).all()
                logger.info(f"Summaries in database: {len(summary_count)}")

                # Count crawl progress
                from core.models.rows import ArxivCrawlProgress

                progress_count = session.exec(select(ArxivCrawlProgress)).all()
                logger.info(f"Crawl progress entries: {len(progress_count)}")

        logger.info("✅ Database information displayed")

    async def run_comprehensive_demo(self):
        """Run the comprehensive demo."""
        logger.info("=== TheArk Comprehensive Demo ===")
        logger.info("This demo will test all major functionality of TheArk")
        logger.info("Database: db/theark.demo.db")

        try:
            # Setup
            await self.setup_database()

            # Core functionality tests
            await self.test_crawl_execution_state()
            await self.test_category_parsing()
            await self.test_progress_tracking()
            await self.test_paper_crawling()  # Added this line

            # Show results
            await self.show_database_info()

            logger.info("\n🎉 Comprehensive demo completed successfully!")
            logger.info("Check the database for detailed results:")
            logger.info(f"  Database: {self.demo_db_path}")
            logger.info("  You can use the web interface to view papers and summaries")

        except Exception as e:
            logger.error(f"❌ Demo failed: {e}")
            raise


async def main():
    """Main function to run the demo."""
    demo = TheArkDemo()
    await demo.run_comprehensive_demo()


if __name__ == "__main__":
    # Run the comprehensive demo
    asyncio.run(main())
