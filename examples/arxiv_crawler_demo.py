"""Simplified demo script for ArxivCrawler with summarization."""

import asyncio
import os
from pathlib import Path

from core import setup_logging
from core.database import SQLiteManager, setup_database_environment
from crawler.arxiv import ArxivCrawler, CrawlConfig, OnDemandCrawlConfig
from crawler.arxiv.core import SummarizationConfig


async def demo_crawler():
    """Demonstrate ArxivCrawler functionality with the Attention paper."""
    setup_logging()

    print("🚀 ArxivCrawler Demo with Summarization")
    print("=" * 50)

    # Remove existing database if it exists
    db_config = setup_database_environment("development")
    db_path = Path(db_config.database_path)
    if db_path.exists():
        db_path.unlink()
        print(f"🗑️  Removed existing database: {db_path}")

    # Setup fresh database
    db_manager = SQLiteManager(str(db_path))
    with db_manager:
        db_manager.create_tables()
        print(f"📊 Database initialized: {db_path}")

    # Check for OpenAI API key
    if not os.environ.get("OPENAI_API_KEY"):
        print("⚠️  OPENAI_API_KEY not set. Summarization disabled.")
        summarization_config = None
    else:
        print("🔑 OpenAI API key found. Summarization enabled!")
        summarization_config = SummarizationConfig(
            summarize_immediately=True,
            use_tools=True,
            model="gpt-4o-mini",
            language="English",
            interest_section="machine learning, artificial intelligence, natural language processing",
        )

    # Create crawler config
    config = CrawlConfig(
        on_demand=OnDemandCrawlConfig(summarization=summarization_config)
    )

    async with ArxivCrawler(db_manager, config=config) as crawler:
        print(f"\n📄 Crawling Attention Is All You Need:")
        print("-" * 30)

        # Crawl the famous Attention paper
        paper_id = "1706.03762"
        print(f"🔄 Crawling: {paper_id}")

        try:
            paper = await crawler.crawl_single_paper(paper_id)
            if not paper:
                print(f"❌ Failed to crawl paper")
                return

            print(f"✅ Success: {paper.arxiv_id}")
            print(f"   📝 Title: {paper.title}")
            print(f"   👥 Authors: {paper.authors}")
            print(f"   📄 Abstract length: {len(paper.abstract)} characters")

            # Get the paper from database to ensure we have the paper_id
            from core.database.repository import PaperRepository

            paper_repo = PaperRepository(db_manager)
            with db_manager:
                stored_paper = paper_repo.get_by_arxiv_id(paper.arxiv_id)

            # Early exit if summarization is not enabled
            if (
                not summarization_config
                or not summarization_config.summarize_immediately
            ):
                print(f"\n⏭️  Summarization disabled")
                return

            # Early exit if paper is not properly stored
            if not stored_paper or not stored_paper.paper_id:
                print(f"\n⏭️  Paper not properly stored in database")
                return

            print(f"\n🧠 Checking summarization...")

            # Wait for summarization to complete
            await asyncio.sleep(3)

            # Check for summary in database
            from core.database.repository import SummaryRepository

            summary_repo = SummaryRepository(db_manager)
            with db_manager:
                summary = summary_repo.get_by_paper_and_language(
                    stored_paper.paper_id, summarization_config.language
                )

            if not summary:
                print(f"⏳ Summary not available")
                return

            print(f"✅ Summarization completed!")
            print(f"   📝 Overview: {summary.overview}")
            print(f"   🎯 Relevance: {summary.relevance}/10")
            print(f"   🔍 Motivation: {summary.motivation}")
            print(f"   🛠️  Method: {summary.method}")
            print(f"   📊 Result: {summary.result}")
            print(f"   🎯 Conclusion: {summary.conclusion}")
            print(f"   🤖 Model: {summary.model}")

        except Exception as e:
            print(f"❌ Error: {e}")

    print(f"\n✅ Demo completed!")


if __name__ == "__main__":
    asyncio.run(demo_crawler())
