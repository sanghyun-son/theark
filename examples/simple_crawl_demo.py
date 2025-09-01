"""Demo for simple crawl strategy: always start from yesterday and skip completed dates."""

import asyncio
from pathlib import Path
from datetime import datetime, timedelta

from core.extractors.concrete.historical_crawl_manager import HistoricalCrawlManager
from core.extractors.concrete.arxiv_source_explorer import ArxivSourceExplorer
from core.database.engine import create_database_engine, create_database_tables
from core.models.rows import CategoryDateProgress
from core.types import Environment
from sqlalchemy.engine import Engine
from sqlmodel import Session


async def setup_completed_dates(engine: Engine) -> None:
    """Setup some completed dates to demonstrate skipping."""
    with Session(engine) as db_session:
        # Mark some dates as completed (should be skipped)
        completed_dates = [
            (datetime.now() - timedelta(days=3)).strftime("%Y-%m-%d"),  # 3 days ago
            (datetime.now() - timedelta(days=4)).strftime("%Y-%m-%d"),  # 4 days ago
            (datetime.now() - timedelta(days=6)).strftime("%Y-%m-%d"),  # 6 days ago
        ]

        for date in completed_dates:
            progress = CategoryDateProgress(
                category="cs.AI",
                date=date,
                is_completed=True,
                papers_found=10,
                papers_stored=10,
            )
            db_session.add(progress)

        db_session.commit()
        print("✅ Setup completed dates for demo")
        print(f"   📅 Completed dates: {completed_dates}")
        print(f"   📅 Will crawl: yesterday and 2 days ago (not completed)")


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
    engine: Engine = create_database_engine(
        Environment.DEVELOPMENT,
        db_path=Path("db/theark.demo.db"),
    )
    create_database_tables(engine)

    # No pre-completed dates - start fresh

    # Create crawl manager
    crawl_manager = HistoricalCrawlManager(
        categories=["cs.AI", "cs.LG"],
        start_date="2025-01-01",  # Start from 2025-01-01 (guaranteed to have papers)
        rate_limit_delay=1.0,
        batch_size=10,
    )

    print(f"\n📊 Initial state:")
    print(f"   Start date: {crawl_manager.start_date}")
    print(f"   End date: {crawl_manager.end_date}")
    print(f"   Today: {datetime.now().strftime('%Y-%m-%d')}")

    # Create source explorer with REAL ArXiv API
    source_explorer = ArxivSourceExplorer(
        api_base_url="https://export.arxiv.org/api/query",  # Real ArXiv API
        delay_seconds=2.0,  # Be respectful to ArXiv API
        max_results_per_request=10,
    )

    print(f"\n🔄 Running crawl cycles...")

    # Run a few cycles to demonstrate
    for i in range(20):
        print(f"\n--- Cycle {i + 1} ---")

        try:
            result = await crawl_manager.run_crawl_cycle(engine, source_explorer)

            if result:
                print(f"✅ Crawled {result.category} on {result.date}")
                print(f"   Papers found: {result.papers_found}")
                print(f"   Papers stored: {result.papers_stored}")
            else:
                # Check if crawling is still active to determine the reason
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
