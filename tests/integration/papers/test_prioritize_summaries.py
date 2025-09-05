"""Integration tests for prioritize_summaries functionality."""

import pytest
from sqlmodel import Session

from core.database.repository.paper.repository import PaperRepository
from core.models.rows import Paper, Summary
from core.services.paper_service import PaperService
from core.types import PaperSummaryStatus


@pytest.mark.asyncio
async def test_prioritize_summaries_with_mock_data(
    mock_db_session: Session, paper_repo: PaperRepository
):
    """Test prioritize_summaries with controlled mock data."""
    # Create test papers with different summary statuses
    papers = [
        Paper(
            arxiv_id="2201.00001",
            title="Paper with DONE summary",
            abstract="Abstract 1",
            authors="Author 1",
            primary_category="cs.AI",
            categories="cs.AI",
            url_abs="http://arxiv.org/abs/2201.00001",
            url_pdf="http://arxiv.org/pdf/2201.00001",
            published_at="2023-01-01",
            summary_status=PaperSummaryStatus.DONE,
        ),
        Paper(
            arxiv_id="2201.00002",
            title="Paper with BATCHED summary",
            abstract="Abstract 2",
            authors="Author 2",
            primary_category="cs.LG",
            categories="cs.LG",
            url_abs="http://arxiv.org/abs/2201.00002",
            url_pdf="http://arxiv.org/pdf/2201.00002",
            published_at="2023-01-02",
            summary_status=PaperSummaryStatus.BATCHED,
        ),
        Paper(
            arxiv_id="2201.00003",
            title="Paper with no summary",
            abstract="Abstract 3",
            authors="Author 3",
            primary_category="cs.CV",
            categories="cs.CV",
            url_abs="http://arxiv.org/abs/2201.00003",
            url_pdf="http://arxiv.org/pdf/2201.00003",
            published_at="2023-01-03",
            summary_status=PaperSummaryStatus.BATCHED,
        ),
        Paper(
            arxiv_id="2201.00004",
            title="Another paper with DONE summary",
            abstract="Abstract 4",
            authors="Author 4",
            primary_category="cs.IR",
            categories="cs.IR",
            url_abs="http://arxiv.org/abs/2201.00004",
            url_pdf="http://arxiv.org/pdf/2201.00004",
            published_at="2023-01-04",
            summary_status=PaperSummaryStatus.DONE,
        ),
    ]

    # Save papers to database
    for paper in papers:
        paper_repo.create(paper)

    # Create summaries for papers with DONE status
    summaries = [
        Summary(
            paper_id=papers[0].paper_id,
            version="v1",
            overview="Overview for paper 1",
            motivation="Motivation for paper 1",
            method="Method for paper 1",
            result="Result for paper 1",
            conclusion="Conclusion for paper 1",
            language="Korean",
            interests="AI,ML",
            relevance=8,
            model="gpt-4",
        ),
        Summary(
            paper_id=papers[3].paper_id,
            version="v1",
            overview="Overview for paper 4",
            motivation="Motivation for paper 4",
            method="Method for paper 4",
            result="Result for paper 4",
            conclusion="Conclusion for paper 4",
            language="Korean",
            interests="IR,Search",
            relevance=7,
            model="gpt-4",
        ),
    ]

    for summary in summaries:
        mock_db_session.add(summary)
    mock_db_session.commit()

    # Test without prioritization
    paper_service = PaperService()
    result_normal = await paper_service.get_papers_lightweight(
        db_session=mock_db_session,
        user_id=None,
        skip=0,
        limit=10,
        language="Korean",
        prioritize_summaries=False,
        sort_by_relevance=False,
    )

    # Test with prioritization
    result_prioritized = await paper_service.get_papers_lightweight(
        db_session=mock_db_session,
        user_id=None,
        skip=0,
        limit=10,
        language="Korean",
        prioritize_summaries=True,
        sort_by_relevance=False,
    )

    print(f"\n=== PRIORITIZE SUMMARIES TEST ===")
    print(f"Normal result: {len(result_normal.papers)} papers")
    print(f"Prioritized result: {len(result_prioritized.papers)} papers")

    # Print paper details
    print(f"\nNormal order:")
    for i, paper in enumerate(result_normal.papers):
        has_summary = paper.has_summary
        status = paper.summary_status
        print(
            f"  {i+1}. ID: {paper.paper_id}, has_summary: {has_summary}, status: {status}"
        )

    print(f"\nPrioritized order:")
    for i, paper in enumerate(result_prioritized.papers):
        has_summary = paper.has_summary
        status = paper.summary_status
        print(
            f"  {i+1}. ID: {paper.paper_id}, has_summary: {has_summary}, status: {status}"
        )

    # Check that prioritized results have summaries first
    prioritized_papers = result_prioritized.papers
    papers_with_summaries = [p for p in prioritized_papers if p.has_summary]
    papers_without_summaries = [p for p in prioritized_papers if not p.has_summary]

    print(
        f"\nPrioritized: {len(papers_with_summaries)} with summaries, {len(papers_without_summaries)} without"
    )

    # Papers with summaries should come first
    if papers_with_summaries and papers_without_summaries:
        first_paper_without_summary_idx = next(
            i for i, p in enumerate(prioritized_papers) if not p.has_summary
        )
        last_paper_with_summary_idx = next(
            i for i, p in enumerate(reversed(prioritized_papers)) if p.has_summary
        )
        last_paper_with_summary_idx = (
            len(prioritized_papers) - 1 - last_paper_with_summary_idx
        )

        print(
            f"First paper without summary at index: {first_paper_without_summary_idx}"
        )
        print(f"Last paper with summary at index: {last_paper_with_summary_idx}")

        assert (
            first_paper_without_summary_idx > last_paper_with_summary_idx
        ), "Papers with summaries should come before papers without summaries"


@pytest.mark.asyncio
async def test_priority_case_logic(
    mock_db_session: Session, paper_repo: PaperRepository
):
    """Test the priority case logic directly."""
    # Create papers with different statuses to test priority ordering
    papers = [
        Paper(
            arxiv_id="2201.00001",
            title="DONE paper",
            abstract="Abstract 1",
            authors="Author 1",
            primary_category="cs.AI",
            categories="cs.AI",
            url_abs="http://arxiv.org/abs/2201.00001",
            url_pdf="http://arxiv.org/pdf/2201.00001",
            published_at="2023-01-01",
            summary_status=PaperSummaryStatus.DONE,
        ),
        Paper(
            arxiv_id="2201.00002",
            title="PROCESSING paper",
            abstract="Abstract 2",
            authors="Author 2",
            primary_category="cs.LG",
            categories="cs.LG",
            url_abs="http://arxiv.org/abs/2201.00002",
            url_pdf="http://arxiv.org/pdf/2201.00002",
            published_at="2023-01-02",
            summary_status=PaperSummaryStatus.PROCESSING,
        ),
        Paper(
            arxiv_id="2201.00003",
            title="BATCHED paper",
            abstract="Abstract 3",
            authors="Author 3",
            primary_category="cs.CV",
            categories="cs.CV",
            url_abs="http://arxiv.org/abs/2201.00003",
            url_pdf="http://arxiv.org/pdf/2201.00003",
            published_at="2023-01-03",
            summary_status=PaperSummaryStatus.BATCHED,
        ),
        Paper(
            arxiv_id="2201.00004",
            title="ERROR paper",
            abstract="Abstract 4",
            authors="Author 4",
            primary_category="cs.IR",
            categories="cs.IR",
            url_abs="http://arxiv.org/abs/2201.00004",
            url_pdf="http://arxiv.org/pdf/2201.00004",
            published_at="2023-01-04",
            summary_status=PaperSummaryStatus.ERROR,
        ),
    ]

    # Save papers to database
    for paper in papers:
        paper_repo.create(paper)

    # Test with prioritization
    paper_service = PaperService()
    result = await paper_service.get_papers_lightweight(
        db_session=mock_db_session,
        user_id=None,
        skip=0,
        limit=10,
        language="Korean",
        prioritize_summaries=True,
        sort_by_relevance=False,
    )

    print(f"\n=== PRIORITY CASE TEST ===")
    print(f"Expected order: DONE (1), PROCESSING (2), ERROR (3), BATCHED (4)")
    print(f"Actual order:")

    for i, paper in enumerate(result.papers):
        status = paper.summary_status
        print(f"  {i+1}. {paper.title} - Status: {status}")

    # Check that DONE comes before PROCESSING, PROCESSING before ERROR, etc.
    status_priority = {
        PaperSummaryStatus.DONE: 1,
        PaperSummaryStatus.PROCESSING: 2,
        PaperSummaryStatus.ERROR: 3,
        PaperSummaryStatus.BATCHED: 4,
    }

    for i in range(len(result.papers) - 1):
        current_priority = status_priority.get(result.papers[i].summary_status, 5)
        next_priority = status_priority.get(result.papers[i + 1].summary_status, 5)

        assert (
            current_priority <= next_priority
        ), f"Priority order violated: {result.papers[i].summary_status} (priority {current_priority}) should come before {result.papers[i + 1].summary_status} (priority {next_priority})"


@pytest.mark.asyncio
async def test_prioritize_summaries_detailed_analysis(
    mock_db_session: Session, paper_repo: PaperRepository
):
    """Detailed test to analyze prioritize_summaries behavior with more papers."""
    # Create more papers to have better statistical analysis
    papers = []
    for i in range(10):
        status = PaperSummaryStatus.DONE if i < 3 else PaperSummaryStatus.BATCHED
        paper = Paper(
            arxiv_id=f"2201.{i:05d}",
            title=f"Test Paper {i+1}",
            abstract=f"Abstract {i+1}",
            authors=f"Author {i+1}",
            primary_category="cs.AI",
            categories="cs.AI",
            url_abs=f"http://arxiv.org/abs/2201.{i:05d}",
            url_pdf=f"http://arxiv.org/pdf/2201.{i:05d}",
            published_at=f"2023-01-{i+1:02d}",
            summary_status=status,
        )
        papers.append(paper)
        paper_repo.create(paper)

    # Create summaries for DONE papers
    for i in range(3):
        summary = Summary(
            paper_id=papers[i].paper_id,
            version="v1",
            overview=f"Overview for paper {i+1}",
            motivation=f"Motivation for paper {i+1}",
            method=f"Method for paper {i+1}",
            result=f"Result for paper {i+1}",
            conclusion=f"Conclusion for paper {i+1}",
            language="Korean",
            interests="AI,ML",
            relevance=8,
            model="gpt-4",
        )
        mock_db_session.add(summary)
    mock_db_session.commit()

    # Test without prioritization
    paper_service = PaperService()
    result_normal = await paper_service.get_papers_lightweight(
        db_session=mock_db_session,
        user_id=None,
        skip=0,
        limit=20,
        language="Korean",
        prioritize_summaries=False,
        sort_by_relevance=False,
    )

    # Test with prioritization
    result_prioritized = await paper_service.get_papers_lightweight(
        db_session=mock_db_session,
        user_id=None,
        skip=0,
        limit=20,
        language="Korean",
        prioritize_summaries=True,
        sort_by_relevance=False,
    )

    print(f"\n=== DETAILED ANALYSIS ===")
    print(f"Total papers in normal: {len(result_normal.papers)}")
    print(f"Total papers in prioritized: {len(result_prioritized.papers)}")

    # Analyze summary status distribution
    normal_statuses = {}
    prioritized_statuses = {}

    for paper in result_normal.papers:
        status = paper.summary_status
        normal_statuses[status] = normal_statuses.get(status, 0) + 1

    for paper in result_prioritized.papers:
        status = paper.summary_status
        prioritized_statuses[status] = prioritized_statuses.get(status, 0) + 1

    print(f"\nNormal status distribution:")
    for status, count in normal_statuses.items():
        print(f"  {status}: {count}")

    print(f"\nPrioritized status distribution:")
    for status, count in prioritized_statuses.items():
        print(f"  {status}: {count}")

    # Check if the first few papers in prioritized have summaries
    print(f"\nFirst 5 papers in prioritized response:")
    for i, paper in enumerate(result_prioritized.papers[:5]):
        has_summary = paper.has_summary
        status = paper.summary_status
        print(
            f"  {i+1}. ID: {paper.paper_id}, has_summary: {has_summary}, status: {status}"
        )

    # The first few papers in prioritized should have summaries
    first_5_prioritized = result_prioritized.papers[:5]
    papers_with_summaries_in_first_5 = sum(
        1 for paper in first_5_prioritized if paper.has_summary
    )

    print(
        f"\nPapers with summaries in first 5 prioritized: {papers_with_summaries_in_first_5}/5"
    )

    # If there are papers with summaries, the first few should have them
    if prioritized_statuses.get(PaperSummaryStatus.DONE, 0) > 0:
        assert (
            papers_with_summaries_in_first_5 > 0
        ), "First papers should have summaries when prioritization is enabled"
