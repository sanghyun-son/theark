"""Demo script for ArxivCrawler functionality."""

import asyncio

from core import setup_logging
from crawler.arxiv import (
    ArxivCrawler,
    CrawlConfig,
    OnDemandCrawlConfig,
    PeriodicCrawlConfig,
)
from crawler.database import SQLiteManager, setup_database_environment


async def on_paper_crawled(paper):
    """Callback when a paper is successfully crawled."""
    print(f"✅ Paper crawled: {paper.arxiv_id} - {paper.title}")


async def on_error(error):
    """Callback when an error occurs."""
    print(f"❌ Error occurred: {error}")


async def demo_crawler():
    """Demonstrate ArxivCrawler functionality."""
    setup_logging()

    print("🚀 ArxivCrawler Demo")
    print("=" * 50)

    # Setup database environment
    db_config = setup_database_environment("development")
    db_path = db_config.database_path
    db_manager = SQLiteManager(db_path)

    # Create tables if they don't exist
    with db_manager:
        db_manager.create_tables()
        print(f"📊 Database initialized: {db_path}")

    # Create crawler with custom config
    config = CrawlConfig(
        on_demand=OnDemandCrawlConfig(
            recent_papers_limit=10,
            monthly_papers_limit=50,
        ),
        periodic=PeriodicCrawlConfig(
            background_interval=5,  # 5 seconds for demo
            recent_papers_limit=10,
        ),
    )

    async with ArxivCrawler(
        db_manager,
        config=config,
        on_paper_crawled=on_paper_crawled,
        on_error=on_error,
    ) as crawler:

        print(f"\n📊 Initial Status:")
        print("-" * 30)
        status = await crawler.get_status()
        print(f"Status: {status.status}")
        print(f"Background Task: {status.background_task_running}")
        print(f"Papers Crawled: {status.on_demand.core.stats.papers_crawled}")
        print(f"Papers Failed: {status.on_demand.core.stats.papers_failed}")

        print(f"\n📄 Crawling Single Papers:")
        print("-" * 30)

        # Test papers to crawl
        test_papers = [
            "1706.03762",  # Attention Is All You Need
            "http://arxiv.org/abs/1706.03762",  # Same paper as URL
            "9999.99999",  # Non-existent paper
        ]

        for paper_id in test_papers:
            print(f"\n🔄 Crawling: {paper_id}")
            try:
                paper = await crawler.crawl_single_paper(paper_id)
                if paper:
                    print(f"   ✅ Success: {paper.arxiv_id}")
                else:
                    print(f"   ❌ Not found or failed")
            except Exception as e:
                print(f"   ❌ Error: {e}")

        print(f"\n🔄 Starting Background Loop (5 seconds):")
        print("-" * 30)

        # Start background loop
        await crawler.start_background_loop()

        # Monitor for a few seconds
        for i in range(3):
            await asyncio.sleep(1)
            status = await crawler.get_status()
            print(
                f"   Status: {status.status}, Background: {status.background_task_running}"
            )

        print(f"\n⏹️  Stopping Background Loop:")
        print("-" * 30)

        # Stop background loop
        await crawler.stop_background_loop()

        print(f"\n📊 Final Status:")
        print("-" * 30)
        status = await crawler.get_status()
        print(f"Status: {status.status}")
        print(f"Background Task: {status.background_task_running}")
        print(f"Papers Crawled: {status.on_demand.core.stats.papers_crawled}")
        print(f"Papers Failed: {status.on_demand.core.stats.papers_failed}")
        print(f"Start Time: {status.on_demand.core.stats.start_time}")

        print(f"\n🔍 Testing Placeholder Methods:")
        print("-" * 30)

        # Test placeholder methods
        recent_papers = await crawler.crawl_recent_papers(limit=5)
        print(f"Recent Papers: {len(recent_papers)} (placeholder)")

        monthly_papers = await crawler.crawl_monthly_papers(2024, 1, limit=10)
        print(f"Monthly Papers: {len(monthly_papers)} (placeholder)")

        print(f"\n✅ Demo completed successfully!")


if __name__ == "__main__":
    asyncio.run(demo_crawler())
