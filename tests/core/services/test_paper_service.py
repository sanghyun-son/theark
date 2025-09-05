"""Tests for PaperService."""

import logging

import pytest
from sqlmodel import Session

from core.database.repository import (
    PaperRepository,
)
from core.extractors.concrete import ArxivExtractor
from core.llm.openai_client import UnifiedOpenAIClient
from core.models import PaperCreateRequest
from core.models.api.responses import (
    PaperResponse,
)
from core.models.rows import Paper
from core.services.paper_service import PaperService
from tests.utils.test_helpers import (
    TestSetupHelper,
)


logger = logging.getLogger(__name__)


@pytest.fixture
def paper_service() -> PaperService:
    """Create PaperService instance."""
    return PaperService()


# =============================================================================
# Paper Creation Tests
# =============================================================================


def test_extract_arxiv_id_from_request(paper_service: PaperService):
    """Test extracting arXiv ID from request."""
    TestSetupHelper.register_test_extractors()

    paper_data = PaperCreateRequest(url="https://arxiv.org/abs/2508.01234")
    arxiv_id = paper_service._extract_arxiv_id(paper_data)
    assert arxiv_id == "2508.01234"


def test_extract_arxiv_id_error_no_identifier(paper_service: PaperService):
    """Test error when no identifier is provided."""
    # Create a PaperCreate with empty URL to test the error case
    paper_data = PaperCreateRequest(url="")
    with pytest.raises(ValueError, match="No URL provided"):
        paper_service._extract_arxiv_id(paper_data)


@pytest.mark.asyncio
async def test_create_paper_new_paper(
    paper_service: PaperService,
    mock_db_session: Session,
    paper_repo: PaperRepository,
    mock_arxiv_extractor: ArxivExtractor,
    mock_openai_client: UnifiedOpenAIClient,
) -> None:
    """Test creating a new paper."""
    # Setup extractor for test
    TestSetupHelper.register_mock_extractors(mock_arxiv_extractor)

    paper_data = PaperCreateRequest(
        url="https://arxiv.org/abs/1706.03762"
    )  # Use predefined paper ID

    # Act
    result = await paper_service.create_paper(
        paper_data, paper_repo, mock_openai_client
    )

    # Assert
    assert isinstance(result, PaperResponse)
    assert result.arxiv_id == "1706.03762"
    assert result.title == "Attention Is All You Need"  # Expected title from mock data

    # Verify paper was saved to database
    saved_paper = paper_repo.get_by_arxiv_id("1706.03762")
    assert saved_paper is not None
    assert saved_paper.arxiv_id == "1706.03762"


@pytest.mark.asyncio
async def test_create_paper_existing_paper(
    paper_service: PaperService,
    saved_paper: Paper,
    mock_db_session: Session,
    mock_arxiv_extractor: ArxivExtractor,
    mock_openai_client: UnifiedOpenAIClient,
) -> None:
    """Test creating paper when it already exists."""
    TestSetupHelper.register_mock_extractors(mock_arxiv_extractor)

    paper_data = PaperCreateRequest(url=f"https://arxiv.org/abs/{saved_paper.arxiv_id}")

    # Create paper repository from session
    paper_repo = PaperRepository(mock_db_session)

    result = await paper_service.create_paper(
        paper_data, paper_repo, mock_openai_client
    )

    assert isinstance(result, PaperResponse)
    assert result.arxiv_id == saved_paper.arxiv_id
    assert result.paper_id == saved_paper.paper_id


# =============================================================================
# Paper Retrieval Tests
# =============================================================================


@pytest.mark.asyncio
async def test_get_paper_by_identifier_arxiv_id(
    paper_service: PaperService,
    saved_paper: Paper,
    mock_db_session: Session,
) -> None:
    """Test getting paper by arXiv ID."""
    result = await paper_service.get_paper(saved_paper.arxiv_id, mock_db_session)

    assert result is not None
    assert result.arxiv_id == saved_paper.arxiv_id
    assert result.paper_id == saved_paper.paper_id


@pytest.mark.asyncio
async def test_get_paper_by_identifier_paper_id(
    paper_service: PaperService,
    saved_paper: Paper,
    mock_db_session: Session,
) -> None:
    """Test getting paper by paper ID."""
    # Act
    result = await paper_service.get_paper(str(saved_paper.paper_id), mock_db_session)

    # Assert
    assert result is not None
    assert result.paper_id == saved_paper.paper_id
    assert result.arxiv_id == saved_paper.arxiv_id


@pytest.mark.asyncio
async def test_get_paper_by_identifier_not_found(
    paper_service: PaperService,
    mock_db_session: Session,
) -> None:
    """Test getting paper by identifier when not found."""
    # Act & Assert
    with pytest.raises(ValueError, match="Paper not found"):
        await paper_service.get_paper("nonexistent", mock_db_session)


# =============================================================================
# CRUD Operations Tests
# =============================================================================


@pytest.mark.asyncio
async def test_create_paper_success(
    paper_service: PaperService,
    mock_db_session: Session,
    mock_openai_client: UnifiedOpenAIClient,
    mock_arxiv_extractor: ArxivExtractor,
) -> None:
    """Test successful paper creation."""
    # Register the mock extractor
    TestSetupHelper.register_mock_extractors(mock_arxiv_extractor)
    paper_data = PaperCreateRequest(
        url="https://arxiv.org/abs/1706.03762",
        skip_auto_summarization=True,
        summary_language="English",
    )

    paper_repo = PaperRepository(mock_db_session)
    result = await paper_service.create_paper(
        paper_data,
        paper_repo,
        mock_openai_client,
        skip_auto_summarization=True,
    )

    assert result.is_starred is False
    assert result.is_read is False
    assert result.summary is None


@pytest.mark.asyncio
async def test_get_papers_lightweight(
    paper_service: PaperService,
    saved_paper,
    saved_summary,
    mock_db_session: Session,
) -> None:
    """Test getting papers with overview only."""
    # Execute
    result = await paper_service.get_papers_lightweight(
        mock_db_session, user_id=1, skip=0, limit=10, language="Korean"
    )

    # Assert
    assert len(result.papers) > 0
    assert result.total_count > 0
    assert result.has_more is not None

    # Check that papers have overview but not full summary
    for paper in result.papers:
        assert hasattr(paper, "overview")
        assert hasattr(paper, "has_summary")
        assert hasattr(paper, "is_starred")
        assert hasattr(paper, "is_read")
        # Should not have full summary object
        assert not hasattr(paper, "summary")


@pytest.mark.asyncio
async def test_paper_prioritization(
    paper_service: PaperService,
    mock_db_session: Session,
    paper_repo: PaperRepository,
) -> None:
    """Test that papers with summaries are prioritized by status."""
    from core.types import PaperSummaryStatus

    # Create test papers with different summary statuses
    papers = [
        # Paper with DONE summary (should be first)
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
        # Paper with ERROR summary (should be third)
        Paper(
            arxiv_id="2201.00002",
            title="Paper with ERROR summary",
            abstract="Abstract 2",
            authors="Author 2",
            primary_category="cs.AI",
            categories="cs.AI",
            url_abs="http://arxiv.org/abs/2201.00002",
            url_pdf="http://arxiv.org/pdf/2201.00002",
            published_at="2023-01-02",
            summary_status=PaperSummaryStatus.ERROR,
        ),
        # Paper with PROCESSING summary (should be second)
        Paper(
            arxiv_id="2201.00003",
            title="Paper with PROCESSING summary",
            abstract="Abstract 3",
            authors="Author 3",
            primary_category="cs.AI",
            categories="cs.AI",
            url_abs="http://arxiv.org/abs/2201.00003",
            url_pdf="http://arxiv.org/pdf/2201.00003",
            published_at="2023-01-03",
            summary_status=PaperSummaryStatus.PROCESSING,
        ),
    ]

    # Save papers to database
    for paper in papers:
        paper_repo.create(paper)

    # Test with prioritization enabled (default)
    result_prioritized = await paper_service.get_papers(
        mock_db_session, user_id=None, skip=0, limit=10, prioritize_summaries=True
    )

    # Test with prioritization disabled
    result_not_prioritized = await paper_service.get_papers(
        mock_db_session, user_id=None, skip=0, limit=10, prioritize_summaries=False
    )

    # Verify we got the expected number of papers
    assert len(result_prioritized.papers) == 3
    assert len(result_not_prioritized.papers) == 3

    # With prioritization: DONE should be first, PROCESSING second, ERROR third
    logger.info(f"Prioritized titles: {result_prioritized.papers}")
    logger.info(f"Not prioritized titles: {result_not_prioritized.papers}")

    prioritized_titles = [paper.title for paper in result_prioritized.papers]
    assert "Paper with DONE summary" in prioritized_titles[0]
    assert "Paper with PROCESSING summary" in prioritized_titles[1]
    assert "Paper with ERROR summary" in prioritized_titles[2]

    # Without prioritization: should be ordered by updated_at (most recent first)
    # Since we created them in order, the last created should be first
    not_prioritized_titles = [paper.title for paper in result_not_prioritized.papers]
    assert "Paper with PROCESSING summary" in not_prioritized_titles[0]  # Most recent
    assert "Paper with ERROR summary" in not_prioritized_titles[1]
    assert "Paper with DONE summary" in not_prioritized_titles[2]  # Oldest
