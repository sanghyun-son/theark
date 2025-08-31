"""Tests for PaperService."""


import pytest
from sqlmodel import Session

from core.database.repository import (
    PaperRepository,
)
from core.extractors import extractor_factory
from core.extractors.concrete import ArxivExtractor
from core.llm.openai_client import UnifiedOpenAIClient
from core.models import PaperCreateRequest
from core.models.api.responses import (
    PaperResponse,
)
from core.models.rows import Paper
from core.services.paper_service import PaperService


@pytest.fixture
def paper_service() -> PaperService:
    """Create PaperService instance."""
    return PaperService()


# =============================================================================
# Paper Creation Tests
# =============================================================================


def test_extract_arxiv_id_from_request(paper_service: PaperService):
    """Test extracting arXiv ID from request."""
    extractor_factory.register_extractor("arxiv", ArxivExtractor())

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
    extractor_factory.register_extractor("arxiv", mock_arxiv_extractor)

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
    extractor_factory.register_extractor("arxiv", mock_arxiv_extractor)

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
    extractor_factory.register_extractor("arxiv", mock_arxiv_extractor)
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
