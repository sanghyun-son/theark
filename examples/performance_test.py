#!/usr/bin/env python3
"""Performance test for optimized paper queries."""

import asyncio
import time
from sqlmodel import Session

from core.database.engine import create_database_engine
from core.database.repository.paper import PaperRepository
from core.database.repository.user import UserStarRepository
from core.database.repository.summary import SummaryRepository
from core.database.repository.summary_read import SummaryReadRepository
from core.models.rows import Paper, Summary, User, UserStar, SummaryRead
from core.types import Environment, PaperSummaryStatus
from core.utils import get_current_timestamp


def create_test_data(engine) -> None:
    """Create test data for performance testing."""
    with Session(engine) as session:
        # Create test user
        user = User(user_id=1, email="test@example.com", display_name="Test User")
        session.add(user)
        session.commit()
        session.refresh(user)

        # Create test papers and summaries
        for i in range(100):  # Create 100 papers
            paper = Paper(
                arxiv_id=f"2101.{i:05d}",
                title=f"Test Paper {i}",
                abstract=f"This is test paper {i} abstract",
                authors=f"Author {i}",
                primary_category="cs.AI",
                categories="cs.AI,cs.LG",
                url_abs=f"https://arxiv.org/abs/2101.{i:05d}",
                url_pdf=f"https://arxiv.org/pdf/2101.{i:05d}",
                published_at="2021-01-01",
                updated_at=get_current_timestamp(),
                summary_status=PaperSummaryStatus.DONE,
            )
            session.add(paper)
            session.commit()
            session.refresh(paper)

            # Create summary for each paper
            summary = Summary(
                paper_id=paper.paper_id,
                version="1.0",
                overview=f"Overview for paper {i}",
                motivation=f"Motivation for paper {i}",
                method=f"Method for paper {i}",
                result=f"Result for paper {i}",
                conclusion=f"Conclusion for paper {i}",
                language="Korean" if i % 2 == 0 else "English",
                interests="AI,ML",
                relevance=8,
                model="gpt-4",
                updated_at=get_current_timestamp(),
            )
            session.add(summary)
            session.commit()
            session.refresh(summary)

            # Create some star and read records
            if (
                i % 3 == 0 and user.user_id and paper.paper_id
            ):  # Every 3rd paper is starred
                star = UserStar(
                    user_id=user.user_id,
                    paper_id=paper.paper_id,
                    note=f"Star note for paper {i}",
                )
                session.add(star)

            if (
                i % 5 == 0 and user.user_id and summary.summary_id
            ):  # Every 5th paper is read
                read = SummaryRead(
                    user_id=user.user_id,
                    summary_id=summary.summary_id,
                    read_at=get_current_timestamp(),
                )
                session.add(read)

        session.commit()
        print(f"Created test data: 100 papers, summaries, and user interactions")


async def test_original_performance(engine) -> float:
    """Test original (non-optimized) query performance."""
    with Session(engine) as session:
        paper_repo = PaperRepository(session)

        start_time = time.time()

        # Simulate original N+1 query pattern
        papers = paper_repo.get_papers_with_summaries(
            skip=0, limit=20, language="Korean"
        )

        # Simulate individual queries for each paper
        for paper in papers:
            if paper.paper_id:
                # Individual summary query (N+1 problem)
                summary_repo = SummaryRepository(session)
                summary = summary_repo.get_by_paper_id_and_language(
                    paper.paper_id, "Korean"
                )

                # Individual star check
                star_repo = UserStarRepository(session)
                is_starred = star_repo.is_paper_starred(1, paper.paper_id)

                # Individual read check
                if summary and summary.summary_id:
                    read_repo = SummaryReadRepository(session)
                    is_read = read_repo.is_summary_read_by_user(1, summary.summary_id)

        end_time = time.time()
        return end_time - start_time


async def test_optimized_performance(engine) -> float:
    """Test optimized query performance."""
    with Session(engine) as session:
        paper_repo = PaperRepository(session)

        start_time = time.time()

        # Use optimized batch query
        paper_overview_data = paper_repo.get_papers_with_overview_optimized(
            skip=0, limit=20, language="Korean"
        )

        # Batch fetch star and read status
        if paper_overview_data:
            paper_ids = [
                data.paper.paper_id
                for data in paper_overview_data
                if data.paper.paper_id
            ]

            # Batch star check
            star_repo = UserStarRepository(session)
            starred_paper_ids = set(star_repo.get_starred_paper_ids(1, paper_ids))

            # Batch read check
            summary_repo = SummaryRepository(session)
            summary_read_repo = SummaryReadRepository(session)

            summary_paper_ids = [
                data.paper.paper_id
                for data in paper_overview_data
                if data.paper.paper_id and data.has_summary
            ]

            summaries = {}
            if summary_paper_ids:
                summaries = summary_repo.get_by_paper_ids_and_language(
                    summary_paper_ids, "Korean"
                )

            summary_ids = [s.summary_id for s in summaries.values() if s.summary_id]
            read_summary_ids = set()
            if summary_ids:
                read_summary_ids = set(
                    summary_read_repo.get_read_summary_ids(1, summary_ids)
                )

        end_time = time.time()
        return end_time - start_time


async def test_join_optimized_performance(engine) -> float:
    """Test JOIN-based optimized query performance."""
    with Session(engine) as session:
        paper_repo = PaperRepository(session)

        start_time = time.time()

        # Use JOIN-based optimized query
        paper_overview_data = paper_repo.get_papers_with_summaries_join(
            skip=0, limit=20, language="Korean"
        )

        # Batch fetch user status
        if paper_overview_data:
            paper_ids = [
                data.paper.paper_id
                for data in paper_overview_data
                if data.paper.paper_id
            ]

            # Batch star check
            star_repo = UserStarRepository(session)
            starred_paper_ids = set(star_repo.get_starred_paper_ids(1, paper_ids))

            # Batch read check
            summary_read_repo = SummaryReadRepository(session)
            summary_repo = SummaryRepository(session)

            summary_paper_ids = [
                data.paper.paper_id
                for data in paper_overview_data
                if data.paper.paper_id and data.has_summary
            ]

            summaries = {}
            if summary_paper_ids:
                summaries = summary_repo.get_by_paper_ids_and_language(
                    summary_paper_ids, "Korean"
                )

            summary_ids = [s.summary_id for s in summaries.values() if s.summary_id]
            read_summary_ids = set()
            if summary_ids:
                read_summary_ids = set(
                    summary_read_repo.get_read_summary_ids(1, summary_ids)
                )

        end_time = time.time()
        return end_time - start_time


async def main():
    """Run performance tests."""
    print("🚀 Performance Test for Paper Query Optimization")
    print("=" * 50)

    # Create test database
    engine = create_database_engine(Environment.TESTING)

    # Create tables
    from core.database.engine import create_database_tables

    create_database_tables(engine)

    # Create test data
    print("📊 Creating test data...")
    create_test_data(engine)

    # Test original performance
    print("⏱️  Testing original (N+1) query performance...")
    original_time = await test_original_performance(engine)
    print(f"   Original time: {original_time:.4f} seconds")

    # Test batch optimized performance
    print("⚡ Testing batch optimized query performance...")
    optimized_time = await test_optimized_performance(engine)
    print(f"   Batch optimized time: {optimized_time:.4f} seconds")

    # Test JOIN optimized performance
    print("🔗 Testing JOIN optimized query performance...")
    join_time = await test_join_optimized_performance(engine)
    print(f"   JOIN optimized time: {join_time:.4f} seconds")

    # Calculate improvements
    batch_improvement = ((original_time - optimized_time) / original_time) * 100
    join_improvement = ((original_time - join_time) / original_time) * 100

    print(f"\n📈 Performance Comparison:")
    print(f"   Original (N+1): {original_time:.4f}s")
    print(
        f"   Batch optimized: {optimized_time:.4f}s ({batch_improvement:.1f}% faster)"
    )
    print(f"   JOIN optimized: {join_time:.4f}s ({join_improvement:.1f}% faster)")

    if join_improvement > batch_improvement:
        print(
            f"✅ JOIN optimization is {join_improvement - batch_improvement:.1f}% better than batch optimization!"
        )
    elif batch_improvement > 0:
        print(f"✅ Batch optimization successful! {batch_improvement:.1f}% faster")
    else:
        print(f"⚠️  No improvement detected")


if __name__ == "__main__":
    asyncio.run(main())
