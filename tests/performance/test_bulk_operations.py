"""Performance tests for bulk operations vs individual operations."""

import logging
import time

import pytest
from sqlmodel import select

from core.database.repository.paper import PaperRepository
from core.database.repository.summary import SummaryRepository
from core.models.rows import Paper, Summary
from core.types import PaperSummaryStatus
from tests.utils.test_helpers import TestDataFactory

logger = logging.getLogger(__name__)


def test_bulk_vs_individual_paper_creation(mock_db_session):
    """Test bulk vs individual paper creation performance."""
    paper_repo = PaperRepository(mock_db_session)

    # Test individual creation
    logger.info("Testing individual paper creation...")
    start_time = time.time()

    for i in range(100):
        # Create test paper using TestDataFactory
        test_paper = TestDataFactory.create_test_paper(
            arxiv_id=f"2508.{i:05d}",
            title=f"Test Paper {i}",
            abstract=f"Abstract for paper {i}",
        )
        paper_repo.create(test_paper)

    individual_time = time.time() - start_time
    logger.info(f"Individual creation: {individual_time:.4f} seconds")

    # Clear database using SQLModel interface
    papers_to_delete = mock_db_session.exec(select(Paper)).all()
    for paper in papers_to_delete:
        mock_db_session.delete(paper)
    mock_db_session.commit()

    # Test bulk creation
    logger.info("Testing bulk paper creation...")
    start_time = time.time()

    # Create test papers using TestDataFactory
    test_papers = [
        TestDataFactory.create_test_paper(
            arxiv_id=f"2508.{i:05d}",
            title=f"Test Paper {i}",
            abstract=f"Abstract for paper {i}",
        )
        for i in range(100)
    ]
    # For Paper objects, we need to use individual create since create_papers_bulk expects ArxivPaper objects
    created_papers = []
    for paper in test_papers:
        created_papers.append(paper_repo.create(paper))

    bulk_time = time.time() - start_time
    logger.info(f"Bulk creation: {bulk_time:.4f} seconds")

    # Calculate improvement
    improvement = (individual_time - bulk_time) / individual_time * 100
    logger.info(f"Performance improvement: {improvement:.1f}%")
    logger.info(f"Speedup: {individual_time / bulk_time:.1f}x")

    assert len(created_papers) == 100, "Should create 100 papers"


def test_bulk_vs_individual_summary_creation(mock_db_session):
    """Test bulk vs individual summary creation performance."""
    # First create some papers
    paper_repo = PaperRepository(mock_db_session)
    for i in range(100):
        test_paper = TestDataFactory.create_test_paper(
            arxiv_id=f"2508.{i:05d}",
            title=f"Test Paper {i}",
            abstract=f"Abstract for paper {i}",
        )
        paper_repo.create(test_paper)

    summary_repo = SummaryRepository(mock_db_session)

    # Test individual summary creation
    logger.info("Testing individual summary creation...")
    start_time = time.time()

    for i in range(100):
        mock_summary = TestDataFactory.create_test_summary(
            paper_id=i + 1,  # paper_id starts from 1
            overview=f"Overview for paper {i}",
            motivation=f"Motivation for paper {i}",
            method=f"Method for paper {i}",
            result=f"Result for paper {i}",
            conclusion=f"Conclusion for paper {i}",
        )
        summary_repo.create(mock_summary)

    individual_time = time.time() - start_time
    logger.info(f"Individual creation: {individual_time:.4f} seconds")

    # Clear summaries using SQLModel interface
    summaries_to_delete = mock_db_session.exec(select(Summary)).all()
    for summary in summaries_to_delete:
        mock_db_session.delete(summary)
    mock_db_session.commit()

    # Test bulk summary creation
    logger.info("Testing bulk summary creation...")
    start_time = time.time()

    mock_summaries = [
        TestDataFactory.create_test_summary(
            paper_id=i + 1,
            overview=f"Overview for paper {i}",
            motivation=f"Motivation for paper {i}",
            method=f"Method for paper {i}",
            result=f"Result for paper {i}",
            conclusion=f"Conclusion for paper {i}",
        )
        for i in range(100)
    ]
    created_summaries = summary_repo.create_summaries_bulk(mock_summaries)

    bulk_time = time.time() - start_time
    logger.info(f"Bulk creation: {bulk_time:.4f} seconds")

    # Calculate improvement
    improvement = (individual_time - bulk_time) / individual_time * 100
    logger.info(f"Performance improvement: {improvement:.1f}%")
    logger.info(f"Speedup: {individual_time / bulk_time:.1f}x")

    assert len(created_summaries) == 100, "Should create 100 summaries"


def test_bulk_vs_individual_status_update(mock_db_session):
    """Test bulk vs individual status update performance."""
    # First create some papers
    paper_repo = PaperRepository(mock_db_session)
    for i in range(100):
        test_paper = TestDataFactory.create_test_paper(
            arxiv_id=f"2508.{i:05d}",
            title=f"Test Paper {i}",
            abstract=f"Abstract for paper {i}",
        )
        paper_repo.create(test_paper)

    # Test individual status update
    logger.info("Testing individual status update...")
    start_time = time.time()

    for i in range(100):
        paper_repo.update_summary_status(i + 1, PaperSummaryStatus.PROCESSING)

    individual_time = time.time() - start_time
    logger.info(f"Individual update: {individual_time:.4f} seconds")

    # Test bulk status update
    logger.info("Testing bulk status update...")
    start_time = time.time()

    paper_ids = list(range(1, 101))  # paper_id starts from 1
    updated_count = paper_repo.update_summary_status_bulk(
        paper_ids, PaperSummaryStatus.DONE
    )

    bulk_time = time.time() - start_time
    logger.info(f"Bulk update: {bulk_time:.4f} seconds")

    # Calculate improvement
    improvement = (individual_time - bulk_time) / individual_time * 100
    logger.info(f"Performance improvement: {improvement:.1f}%")
    logger.info(f"Speedup: {individual_time / bulk_time:.1f}x")

    assert updated_count == 100, "Should update 100 papers"


if __name__ == "__main__":
    logger.info("🚀 Performance Test: Bulk vs Individual Operations")
    logger.info("=" * 50)
    logger.info("Note: Run with pytest to use mock_db_session fixture")
    logger.info("Example: pytest tests/performance/test_bulk_operations.py -v")
