"""Tests for StatisticsService."""

import pytest
from datetime import datetime
from sqlmodel import Session

from core.models.rows import Paper, Summary
from core.models.api.responses import StatisticsResponse
from core.services.statistics_service import StatisticsService


@pytest.fixture
def statistics_db_session(mock_db_engine) -> Session:
    """Provide an isolated database session for statistics tests."""
    with Session(mock_db_engine) as session:
        yield session


@pytest.fixture
def statistics_service(statistics_db_session: Session) -> StatisticsService:
    """Provide a StatisticsService instance."""
    return StatisticsService(statistics_db_session)


@pytest.fixture
def statistics_test_papers() -> list[Paper]:
    """Provide test papers for statistics testing."""
    return [
        Paper(
            paper_id=100,
            arxiv_id="1001.0001",
            title="Test Paper 1",
            authors="Author 1, Author 2",
            abstract="Test abstract 1",
            primary_category="cs.AI",
            categories="cs.AI",
            url_abs="http://arxiv.org/abs/1001.0001",
            published_at="2024-01-01T00:00:00Z",
        ),
        Paper(
            paper_id=101,
            arxiv_id="1001.0002",
            title="Test Paper 2",
            authors="Author 3, Author 4",
            abstract="Test abstract 2",
            primary_category="cs.ML",
            categories="cs.ML",
            url_abs="http://arxiv.org/abs/1001.0002",
            published_at="2024-01-02T00:00:00Z",
        ),
        Paper(
            paper_id=102,
            arxiv_id="1001.0003",
            title="Test Paper 3",
            authors="Author 5, Author 6",
            abstract="Test abstract 3",
            primary_category="cs.CV",
            categories="cs.CV",
            url_abs="http://arxiv.org/abs/1001.0003",
            published_at="2024-01-03T00:00:00Z",
        ),
    ]


@pytest.fixture
def sample_statistics_summaries() -> list[Summary]:
    """Provide test summaries for statistics testing."""
    return [
        Summary(
            summary_id=1,
            paper_id=100,  # Match with statistics_test_papers[0].paper_id
            version="1.0",
            overview="Test overview 1",
            motivation="Test motivation 1",
            method="Test method 1",
            result="Test result 1",
            conclusion="Test conclusion 1",
            language="Korean",
            interests="ML, NLP",
            relevance=8,
            model="gpt-4",
        ),
        Summary(
            summary_id=2,
            paper_id=101,  # Match with statistics_test_papers[1].paper_id
            version="1.0",
            overview="Test overview 2",
            motivation="Test motivation 2",
            method="Test method 2",
            result="Test result 2",
            conclusion="Test conclusion 2",
            language="Korean",
            interests="CV, DL",
            relevance=9,
            model="gpt-4",
        ),
    ]


@pytest.fixture
def saved_papers_with_summaries(
    statistics_db_session: Session,
    statistics_test_papers: list[Paper],
    sample_statistics_summaries: list[Summary],
) -> None:
    """Save test papers and summaries to the database."""
    for paper in statistics_test_papers:
        statistics_db_session.add(paper)
    for summary in sample_statistics_summaries:
        statistics_db_session.add(summary)
    statistics_db_session.commit()


def test_statistics_service_initialization(
    statistics_service: StatisticsService,
) -> None:
    """Test StatisticsService initialization."""
    assert statistics_service is not None
    assert hasattr(statistics_service, "db")


def test_get_application_statistics_empty_database(
    statistics_service: StatisticsService,
) -> None:
    """Test statistics with empty database."""
    stats = statistics_service.get_application_statistics()

    assert stats.total_papers == 0
    assert stats.papers_with_summary == 0
    assert stats.papers_without_summary == 0
    assert stats.batch_requested_summaries == 0
    assert stats.summary_coverage_percentage == 0.0
    assert isinstance(stats.last_updated, str)


def test_get_application_statistics_with_papers_only(
    statistics_service: StatisticsService,
    saved_papers_with_summaries: None,
) -> None:
    """Test statistics with papers but no summaries."""
    # Remove summaries to test papers-only scenario
    with statistics_service.db as session:
        session.exec(Summary.__table__.delete())
        session.commit()

    stats = statistics_service.get_application_statistics()

    assert stats.total_papers == 3
    assert stats.papers_with_summary == 0
    assert stats.papers_without_summary == 3
    assert stats.batch_requested_summaries == 0
    assert stats.summary_coverage_percentage == 0.0


def test_get_application_statistics_with_papers_and_summaries(
    statistics_service: StatisticsService,
    saved_papers_with_summaries: None,
) -> None:
    """Test statistics with both papers and summaries."""
    stats = statistics_service.get_application_statistics()

    assert stats.total_papers == 3
    assert stats.papers_with_summary == 2
    assert stats.papers_without_summary == 1
    assert stats.batch_requested_summaries == 2
    assert stats.summary_coverage_percentage == pytest.approx(66.67, abs=0.01)


def test_get_application_statistics_coverage_calculation(
    statistics_service: StatisticsService,
) -> None:
    """Test coverage percentage calculation."""
    # Test with 0 papers
    stats = StatisticsResponse.create(
        total_papers=0,
        papers_with_summary=0,
        batch_requested_summaries=0,
        last_updated="2024-01-01T00:00:00",
    )
    assert stats.summary_coverage_percentage == 0.0

    # Test with 100% coverage
    stats = StatisticsResponse.create(
        total_papers=10,
        papers_with_summary=10,
        batch_requested_summaries=10,
        last_updated="2024-01-01T00:00:00",
    )
    assert stats.summary_coverage_percentage == 100.0

    # Test with 50% coverage
    stats = StatisticsResponse.create(
        total_papers=10,
        papers_with_summary=5,
        batch_requested_summaries=5,
        last_updated="2024-01-01T00:00:00",
    )
    assert stats.summary_coverage_percentage == 50.0


def test_get_application_statistics_auto_calculated_fields(
    statistics_service: StatisticsService,
    saved_papers_with_summaries: None,
) -> None:
    """Test that auto-calculated fields are computed correctly."""
    stats = statistics_service.get_application_statistics()

    # papers_without_summary should be auto-calculated
    expected_without_summary = stats.total_papers - stats.papers_with_summary
    assert stats.papers_without_summary == expected_without_summary

    # summary_coverage_percentage should be auto-calculated
    expected_coverage = (stats.papers_with_summary / stats.total_papers) * 100
    assert stats.summary_coverage_percentage == pytest.approx(
        expected_coverage, abs=0.01
    )


def test_get_application_statistics_timestamp_format(
    statistics_service: StatisticsService,
) -> None:
    """Test that last_updated timestamp is in ISO format."""
    stats = statistics_service.get_application_statistics()

    # Should be a valid ISO format string
    datetime.fromisoformat(stats.last_updated)
