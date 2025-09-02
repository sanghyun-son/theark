"""Demo for simple crawl strategy: always start from yesterday and skip completed dates."""

import asyncio
import logging
from datetime import datetime
from pathlib import Path

from sqlalchemy.engine import Engine

from core.database.engine import create_database_engine, create_database_tables
from core.extractors.concrete.arxiv_source_explorer import ArxivSourceExplorer
from core.extractors.concrete.historical_crawl_manager import HistoricalCrawlManager
from core.types import Environment

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
        batch_size=100,  # 10 → 100으로 증가
    )
    print("✅ Crawl manager created")

    print("\n📊 Initial state:")
    print(f"   End date: {crawl_manager.end_date}")
    print(f"   Today: {datetime.now().strftime('%Y-%m-%d')}")
    print("   Will start from: yesterday")

    # Create source explorer with REAL ArXiv API
    print("🔧 Creating ArXiv source explorer...")
    source_explorer = ArxivSourceExplorer(
        api_base_url="https://export.arxiv.org/api/query",  # Real ArXiv API
        delay_seconds=2.0,  # Be respectful to ArXiv API
        max_results_per_request=100,  # 10 → 100으로 증가
    )
    print("✅ ArXiv source explorer created")

    print("\n🔄 Running crawl cycles...")

    # Start the crawl manager
    print("🚀 Starting crawl manager...")
    await crawl_manager.start(source_explorer, engine)
    print("✅ Crawl manager started")

    # Wait a bit for initial crawl cycles
    print("⏳ Waiting for initial crawl cycles...")
    await asyncio.sleep(50)

    # Check status
    print(
        f"📊 Crawl manager status: {'Running' if crawl_manager.is_running else 'Stopped'}"
    )
    print(
        f"📈 Current progress: {crawl_manager.current_date} | Category: {crawl_manager.current_category_index}"
    )

    # Stop the crawl manager
    print("🛑 Stopping crawl manager...")
    await crawl_manager.stop()
    print("✅ Crawl manager stopped")

    print("\n🎉 Simple crawl demo completed!")


if __name__ == "__main__":
    asyncio.run(main())
