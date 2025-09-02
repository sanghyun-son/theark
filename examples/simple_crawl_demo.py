"""Demo for simple crawl strategy: always start from yesterday and skip completed dates."""

import asyncio
import logging
from pathlib import Path
from datetime import datetime, timedelta

from core.extractors.concrete.historical_crawl_manager import HistoricalCrawlManager
from core.extractors.concrete.arxiv_source_explorer import ArxivSourceExplorer
from core.database.engine import create_database_engine, create_database_tables
from core.types import Environment
from sqlalchemy.engine import Engine

# Set up logging
logging.basicConfig(level=logging.DEBUG, format="%(levelname)s:%(name)s:%(message)s")
logger = logging.getLogger(__name__)


async def main() -> None:
    """Run simple crawl demo."""
    print("🚀 Simple Crawl Strategy Demo")
    print("=" * 50)
    print("🎯 Strategy:")
    print("   • Always start from yesterday")
    print("   • Skip already completed dates")
    print("   • Simple and intuitive")
    print("=" * 50)

    # Initialize database
    print("🔧 Initializing database...")
    engine: Engine = create_database_engine(
        Environment.DEVELOPMENT,
        db_path=Path("db/theark.demo.db"),
    )
    print("✅ Database engine created")

    create_database_tables(engine)
    print("✅ Database tables created")

    # Create crawl manager
    print("🔧 Creating crawl manager...")
    crawl_manager = HistoricalCrawlManager(
        categories=["cs.AI", "cs.LG"],
        rate_limit_delay=1.0,
        batch_size=10,
    )
    print("✅ Crawl manager created")

    print(f"\n📊 Initial state:")
    print(f"   End date: {crawl_manager.end_date}")
    print(f"   Today: {datetime.now().strftime('%Y-%m-%d')}")
    print(f"   Will start from: yesterday")

    # Create source explorer with REAL ArXiv API
    print("🔧 Creating ArXiv source explorer...")
    source_explorer = ArxivSourceExplorer(
        api_base_url="https://export.arxiv.org/api/query",  # Real ArXiv API
        delay_seconds=2.0,  # Be respectful to ArXiv API
        max_results_per_request=10,
    )
    print("✅ ArXiv source explorer created")

    print(f"\n🔄 Running crawl cycles...")

    # Run a few cycles to demonstrate
    for i in range(20):
        print(f"\n--- Cycle {i + 1} ---")

        try:
            print(f"🔄 Running crawl cycle {i + 1}...")
            result = await crawl_manager.run_crawl_cycle(engine, source_explorer)

            if result:
                print(f"✅ Crawled {result.category} on {result.date}")
                print(f"   Papers found: {result.papers_found}")
                print(f"   Papers stored: {result.papers_stored}")
            else:
                # Check if crawling is still active to determine the reason
                print("📊 Getting progress summary...")
                summary = crawl_manager.get_progress_summary(engine)
                if summary.is_active:
                    print("⏭️  Date-category already completed, skipped")
                else:
                    print("🏁 No more date-category combinations to process")

            # Get progress summary
            summary = crawl_manager.get_progress_summary(engine)
            print(
                f"📈 Current: {summary.current_date} | Category: {summary.current_category_index}"
            )

        except Exception as e:
            print(f"❌ Error in cycle {i + 1}: {e}")
            break

    print(f"\n🎉 Simple crawl demo completed!")


if __name__ == "__main__":
    asyncio.run(main())
