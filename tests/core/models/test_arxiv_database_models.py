"""Tests for ArXiv database models."""

import pytest
from sqlmodel import Session

from core.models.rows import ArxivCrawlProgress, ArxivFailedPaper
from core.utils import get_current_timestamp


@pytest.fixture
def sample_crawl_progress() -> ArxivCrawlProgress:
    """Create a sample crawl progress record."""
    return ArxivCrawlProgress(
        category="cs.AI",
        last_crawled_date="2024-01-15",
        last_crawled_index=42,
        is_active=True,
    )


@pytest.fixture
def sample_failed_paper() -> ArxivFailedPaper:
    """Create a sample failed paper record."""
    return ArxivFailedPaper(
        arxiv_id="2401.12345",
        category="cs.AI",
        error_message="Network timeout",
        retry_count=2,
    )


def test_arxiv_crawl_progress_creation(
    sample_crawl_progress: ArxivCrawlProgress,
) -> None:
    """Test ArxivCrawlProgress model creation."""
    assert sample_crawl_progress.category == "cs.AI"
    assert sample_crawl_progress.last_crawled_date == "2024-01-15"
    assert sample_crawl_progress.last_crawled_index == 42
    assert sample_crawl_progress.is_active is True
    assert sample_crawl_progress.progress_id is None  # Not yet saved


def test_arxiv_crawl_progress_defaults() -> None:
    """Test ArxivCrawlProgress default values."""
    progress = ArxivCrawlProgress(
        category="cs.LG",
        last_crawled_date="2024-01-15",
    )

    assert progress.last_crawled_index == 0
    assert progress.is_active is True
    assert progress.created_at is not None
    assert progress.updated_at is not None


def test_arxiv_failed_paper_creation(sample_failed_paper: ArxivFailedPaper) -> None:
    """Test ArxivFailedPaper model creation."""
    assert sample_failed_paper.arxiv_id == "2401.12345"
    assert sample_failed_paper.category == "cs.AI"
    assert sample_failed_paper.error_message == "Network timeout"
    assert sample_failed_paper.retry_count == 2
    assert sample_failed_paper.failed_id is None  # Not yet saved


def test_arxiv_failed_paper_defaults() -> None:
    """Test ArxivFailedPaper default values."""
    failed_paper = ArxivFailedPaper(
        arxiv_id="2401.12345",
        category="cs.AI",
        error_message="Test error",
    )

    assert failed_paper.retry_count == 0
    assert failed_paper.last_retry_at is None
    assert failed_paper.created_at is not None
    assert failed_paper.updated_at is not None


def test_arxiv_crawl_progress_database_operations(
    mock_db_session: Session, sample_crawl_progress: ArxivCrawlProgress
) -> None:
    """Test ArxivCrawlProgress database operations."""
    # Add to database
    mock_db_session.add(sample_crawl_progress)
    mock_db_session.commit()
    mock_db_session.refresh(sample_crawl_progress)

    # Verify it was saved
    assert sample_crawl_progress.progress_id is not None

    # Query from database
    retrieved = mock_db_session.get(
        ArxivCrawlProgress, sample_crawl_progress.progress_id
    )
    assert retrieved is not None
    assert retrieved.category == "cs.AI"
    assert retrieved.last_crawled_date == "2024-01-15"
    assert retrieved.last_crawled_index == 42


def test_arxiv_failed_paper_database_operations(
    mock_db_session: Session, sample_failed_paper: ArxivFailedPaper
) -> None:
    """Test ArxivFailedPaper database operations."""
    # Add to database
    mock_db_session.add(sample_failed_paper)
    mock_db_session.commit()
    mock_db_session.refresh(sample_failed_paper)

    # Verify it was saved
    assert sample_failed_paper.failed_id is not None

    # Query from database
    retrieved = mock_db_session.get(ArxivFailedPaper, sample_failed_paper.failed_id)
    assert retrieved is not None
    assert retrieved.arxiv_id == "2401.12345"
    assert retrieved.category == "cs.AI"
    assert retrieved.error_message == "Network timeout"
    assert retrieved.retry_count == 2


def test_arxiv_crawl_progress_update(mock_db_session: Session) -> None:
    """Test updating ArxivCrawlProgress."""
    progress = ArxivCrawlProgress(
        category="cs.CL",
        last_crawled_date="2024-01-15",
        last_crawled_index=10,
    )

    mock_db_session.add(progress)
    mock_db_session.commit()
    mock_db_session.refresh(progress)

    # Update the progress
    progress.last_crawled_index = 25
    progress.last_crawled_date = "2024-01-16"
    mock_db_session.commit()
    mock_db_session.refresh(progress)

    assert progress.last_crawled_index == 25
    assert progress.last_crawled_date == "2024-01-16"


def test_arxiv_failed_paper_retry_tracking(mock_db_session: Session) -> None:
    """Test retry tracking in ArxivFailedPaper."""
    failed_paper = ArxivFailedPaper(
        arxiv_id="2401.12345",
        category="cs.AI",
        error_message="Initial error",
        retry_count=1,
    )

    mock_db_session.add(failed_paper)
    mock_db_session.commit()
    mock_db_session.refresh(failed_paper)

    # Simulate a retry
    failed_paper.retry_count += 1
    failed_paper.last_retry_at = get_current_timestamp()
    failed_paper.error_message = "Retry error"
    mock_db_session.commit()
    mock_db_session.refresh(failed_paper)

    assert failed_paper.retry_count == 2
    assert failed_paper.last_retry_at is not None
    assert failed_paper.error_message == "Retry error"
