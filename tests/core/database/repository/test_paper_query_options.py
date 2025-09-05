"""Tests for PaperRepository query options."""

import logging

import pytest
from sqlmodel import Session

from core.database.repository.paper import PaperRepository
from core.models.rows import Paper, PaperSummaryStatus, Summary
from tests.utils.test_helpers import TestDataFactory

logger = logging.getLogger(__name__)


# =============================================================================
# Query Option Tests
# =============================================================================


def test_default_sorting_timestamp_only(
    paper_repo: PaperRepository, saved_papers: list[Paper]
):
    """Test default sorting by timestamp only."""
    papers = paper_repo.get_papers_with_overview_optimized(
        skip=0,
        limit=10,
        prioritize_summaries=False,
        sort_by_relevance=False,
    )

    # Should return papers ordered by updated_at DESC (newest first)
    assert len(papers) >= 3
    # Verify they are ordered by updated_at DESC
    for i in range(len(papers) - 1):
        assert papers[i].updated_at >= papers[i + 1].updated_at


def test_summary_priority_sorting(
    paper_repo: PaperRepository, mock_db_session: Session
):
    """Test sorting by summary status priority only."""
    # Create test papers with different summary statuses
    paper_done = TestDataFactory.create_test_paper(
        arxiv_id="test.done",
        title="Paper with DONE Summary",
        summary_status=PaperSummaryStatus.DONE,
    )
    paper_processing = TestDataFactory.create_test_paper(
        arxiv_id="test.processing",
        title="Paper with PROCESSING Summary",
        summary_status=PaperSummaryStatus.PROCESSING,
    )
    paper_error = TestDataFactory.create_test_paper(
        arxiv_id="test.error",
        title="Paper with ERROR Summary",
        summary_status=PaperSummaryStatus.ERROR,
    )
    paper_none = TestDataFactory.create_test_paper(
        arxiv_id="test.none",
        title="Paper with No Summary",
        summary_status=None,
    )

    # Save papers
    paper_repo.create(paper_done)
    paper_repo.create(paper_processing)
    paper_repo.create(paper_error)
    paper_repo.create(paper_none)

    papers = paper_repo.get_papers_with_overview_optimized(
        skip=0,
        limit=10,
        prioritize_summaries=True,
        sort_by_relevance=False,
    )

    # Should return papers ordered by summary status priority
    assert len(papers) >= 4
    titles = [paper.title for paper in papers]

    # DONE should be first, then PROCESSING, then ERROR, then None
    assert "Paper with DONE Summary" in titles[0]
    assert "Paper with PROCESSING Summary" in titles[1]
    assert "Paper with ERROR Summary" in titles[2]
    assert "Paper with No Summary" in titles[3]


def test_relevance_sorting_only(paper_repo: PaperRepository, mock_db_session: Session):
    """Test sorting by relevance score only."""
    # Create papers with summaries of different relevance scores
    paper_high = TestDataFactory.create_test_paper(
        arxiv_id="test.high",
        title="High Relevance Paper",
        summary_status=PaperSummaryStatus.DONE,
    )
    paper_medium = TestDataFactory.create_test_paper(
        arxiv_id="test.medium",
        title="Medium Relevance Paper",
        summary_status=PaperSummaryStatus.DONE,
    )
    paper_low = TestDataFactory.create_test_paper(
        arxiv_id="test.low",
        title="Low Relevance Paper",
        summary_status=PaperSummaryStatus.DONE,
    )

    # Save papers
    paper_repo.create(paper_high)
    paper_repo.create(paper_medium)
    paper_repo.create(paper_low)

    # Create summaries with different relevance scores
    summary_high = TestDataFactory.create_test_summary(
        paper_id=paper_high.paper_id,
        language="Korean",
        relevance=9,
    )
    summary_medium = TestDataFactory.create_test_summary(
        paper_id=paper_medium.paper_id,
        language="Korean",
        relevance=6,
    )
    summary_low = TestDataFactory.create_test_summary(
        paper_id=paper_low.paper_id,
        language="Korean",
        relevance=3,
    )

    # Save summaries
    mock_db_session.add(summary_high)
    mock_db_session.add(summary_medium)
    mock_db_session.add(summary_low)
    mock_db_session.commit()

    papers = paper_repo.get_papers_with_overview_optimized(
        skip=0,
        limit=10,
        prioritize_summaries=False,
        sort_by_relevance=True,
        language="Korean",
    )

    # Should return papers ordered by relevance score DESC
    assert len(papers) >= 3
    titles = [paper.title for paper in papers]

    # High relevance (9) should be first, then medium (6), then low (3)
    assert "High Relevance Paper" in titles[0]
    assert "Medium Relevance Paper" in titles[1]
    assert "Low Relevance Paper" in titles[2]


def test_category_filtering(paper_repo: PaperRepository, mock_db_session: Session):
    """Test filtering by categories."""
    # Create papers with different categories
    paper_ai = TestDataFactory.create_test_paper(
        arxiv_id="test.ai",
        title="AI Paper",
        primary_category="cs.AI",
        categories="cs.AI,cs.LG",
    )
    paper_cv = TestDataFactory.create_test_paper(
        arxiv_id="test.cv",
        title="CV Paper",
        primary_category="cs.CV",
        categories="cs.CV",
    )
    paper_cl = TestDataFactory.create_test_paper(
        arxiv_id="test.cl",
        title="CL Paper",
        primary_category="cs.CL",
        categories="cs.CL",
    )

    # Save papers
    paper_repo.create(paper_ai)
    paper_repo.create(paper_cv)
    paper_repo.create(paper_cl)

    # Filter by cs.AI category
    papers = paper_repo.get_papers_with_overview_optimized(
        skip=0,
        limit=10,
        prioritize_summaries=False,
        sort_by_relevance=False,
        categories=["cs.AI"],
    )

    # Should only return papers with cs.AI category
    assert len(papers) >= 1
    titles = [paper.title for paper in papers]
    assert "AI Paper" in titles
    assert "CV Paper" not in titles
    assert "CL Paper" not in titles


def test_combined_filtering_and_sorting(
    paper_repo: PaperRepository, mock_db_session: Session
):
    """Test combining category filtering with relevance sorting."""
    # Create papers with cs.AI category and different relevance scores
    paper_high = TestDataFactory.create_test_paper(
        arxiv_id="test.ai.high",
        title="High Relevance AI Paper",
        primary_category="cs.AI",
        categories="cs.AI",
        summary_status=PaperSummaryStatus.DONE,
    )
    paper_medium = TestDataFactory.create_test_paper(
        arxiv_id="test.ai.medium",
        title="Medium Relevance AI Paper",
        primary_category="cs.AI",
        categories="cs.AI",
        summary_status=PaperSummaryStatus.DONE,
    )

    # Save papers
    paper_repo.create(paper_high)
    paper_repo.create(paper_medium)

    # Create summaries with different relevance scores
    summary_high = TestDataFactory.create_test_summary(
        paper_id=paper_high.paper_id,
        language="Korean",
        relevance=9,
    )
    summary_medium = TestDataFactory.create_test_summary(
        paper_id=paper_medium.paper_id,
        language="Korean",
        relevance=6,
    )

    # Save summaries
    mock_db_session.add(summary_high)
    mock_db_session.add(summary_medium)
    mock_db_session.commit()

    # Filter by cs.AI category and sort by relevance
    papers = paper_repo.get_papers_with_overview_optimized(
        skip=0,
        limit=10,
        prioritize_summaries=False,
        sort_by_relevance=True,
        categories=["cs.AI"],
        language="Korean",
    )

    # Should return only cs.AI papers, ordered by relevance
    assert len(papers) >= 2
    titles = [paper.title for paper in papers]

    # High relevance (9) should be first, then medium (6)
    assert "High Relevance AI Paper" in titles[0]
    assert "Medium Relevance AI Paper" in titles[1]


def test_pagination_with_query_options(
    paper_repo: PaperRepository, saved_papers: list[Paper]
):
    """Test pagination works with query options."""
    # Get first page
    papers_page1 = paper_repo.get_papers_with_overview_optimized(
        skip=0,
        limit=2,
        prioritize_summaries=True,
        sort_by_relevance=False,
    )

    # Get second page
    papers_page2 = paper_repo.get_papers_with_overview_optimized(
        skip=2,
        limit=2,
        prioritize_summaries=True,
        sort_by_relevance=False,
    )

    # Should get different papers (first page should have 2, second page may have fewer)
    assert len(papers_page1) == 2
    assert len(papers_page2) >= 0  # Second page may be empty or have fewer papers

    page1_titles = [paper.title for paper in papers_page1]
    page2_titles = [paper.title for paper in papers_page2]

    # No overlap between pages (if second page has papers)
    if page2_titles:
        assert not any(title in page2_titles for title in page1_titles)
