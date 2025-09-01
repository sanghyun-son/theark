"""Demo for historical ArXiv crawling from yesterday backwards."""

import asyncio
from datetime import datetime, timedelta
from typing import Sequence

from core.explorers.historical_crawl_manager import HistoricalCrawlManager
from core.database.engine import create_database_engine, create_database_tables
from core.types import Environment
from sqlalchemy.engine import Engine


async def main() -> None:
    """Run historical crawl demo."""
    print("🚀 Historical ArXiv Crawling Demo")
    print("=" * 50)

    # Initialize database
    engine: Engine = create_database_engine(Environment.TESTING)
    create_database_tables(engine)

    # Define categories to crawl
    categories: Sequence[str] = ["cs.AI", "cs.LG", "cs.CL"]

    # Start from yesterday
    yesterday: str = (datetime.now() - timedelta(days=1)).strftime("%Y-%m-%d")

    print(f"📊 Categories: {categories}")
    print(f"📅 Start date: {yesterday}")
    print(f"🎯 End date: 2015-01-01")
    print(f"⏱️  Rate limit: 10 seconds between requests")
    print(f"📦 Batch size: 100 papers per request")
    print()

    # Create historical crawl manager
    crawl_manager: HistoricalCrawlManager = HistoricalCrawlManager(
        categories=categories, start_date=yesterday
    )

    # Run a few cycles to demonstrate
    print("🔄 Running crawl cycles...")

    from sqlmodel import Session

    # Run 5 cycles to demonstrate
    for i in range(5):
        print(f"\n--- Cycle {i + 1} ---")

        try:
            await crawl_manager.run_crawl_cycle(engine)

            # Get progress summary
            summary = crawl_manager.get_progress_summary(engine)

            print(f"📈 Progress Summary:")
            print(f"   Active: {summary['is_active']}")
            print(f"   Current date: {summary['current_date']}")
            print(f"   Current category: {summary['current_category']}")
            print(
                f"   Completed date-categories: {summary['completed_date_categories']}"
            )
            print(f"   Failed date-categories: {summary['failed_date_categories']}")
            print(f"   Total papers found: {summary['total_papers_found']}")
            print(f"   Total papers stored: {summary['total_papers_stored']}")

            # Check if crawling is complete
            if not summary["is_active"]:
                print("✅ Historical crawling completed!")
                break

        except Exception as e:
            print(f"❌ Error in cycle {i + 1}: {e}")
            break

    print("\n🎉 Demo completed!")


if __name__ == "__main__":
    asyncio.run(main())
