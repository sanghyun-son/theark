"""Tests for paper creation service."""

from unittest.mock import AsyncMock, patch

import pytest

from api.services.paper_creation_service import PaperCreationService
from core.models import PaperCreateRequest as PaperCreate
from core.models.database.entities import PaperEntity
from core.extractors import extractor_factory
from core.extractors.concrete import ArxivExtractor


def test_extract_arxiv_id_from_request():
    """Test extracting arXiv ID from request."""
    # Setup extractor for test
    extractor_factory.register_extractor("arxiv", ArxivExtractor())

    service = PaperCreationService()
    paper_data = PaperCreate(url="https://arxiv.org/abs/2508.01234")
    arxiv_id = service._extract_arxiv_id(paper_data)
    assert arxiv_id == "2508.01234"


def test_extract_arxiv_id_error_no_identifier():
    """Test error when no identifier is provided."""

    class MockPaperData:
        def __init__(self):
            self.url = None

    service = PaperCreationService()
    paper_data = MockPaperData()
    with pytest.raises(ValueError, match="No URL provided"):
        service._extract_arxiv_id(paper_data)


@pytest.fixture
def mock_paper():
    """Create a mock PaperEntity for testing."""
    return PaperEntity(
        paper_id=1,
        arxiv_id="2508.01234",
        title="Test Paper Title",
        abstract="Test paper abstract",
        primary_category="cs.AI",
        categories="cs.AI,cs.LG",
        authors="Author One;Author Two",
        url_abs="https://arxiv.org/abs/2508.01234",
        url_pdf="https://arxiv.org/pdf/2508.01234",
        published_at="2023-08-01T00:00:00Z",
        updated_at="2023-08-01T00:00:00Z",
    )


@pytest.mark.asyncio
@patch("api.services.paper_creation_service.PaperRepository")
async def test_create_paper_new_paper(
    mock_repo_class,
    mock_db_manager,
    mock_paper,
):
    """Test creating a new paper."""
    # Setup extractor for test
    extractor_factory.register_extractor("arxiv", ArxivExtractor())

    # Mock repository
    mock_repo = mock_repo_class.return_value
    mock_repo.get_by_arxiv_id = AsyncMock(return_value=None)
    mock_repo.create = AsyncMock(return_value=1)

    paper_creation_service = PaperCreationService()
    paper_creation_service._extract_paper = AsyncMock(return_value=mock_paper)

    paper_data = PaperCreate(url="https://arxiv.org/abs/2508.01234")
    result = await paper_creation_service.create_paper(paper_data, mock_db_manager)

    assert isinstance(result, PaperEntity)
    assert result.arxiv_id == "2508.01234"
    assert result.title == "Test Paper Title"


@pytest.mark.asyncio
@patch("api.services.paper_creation_service.PaperRepository")
async def test_create_paper_existing_paper(
    mock_repo_class,
    mock_db_manager,
    mock_paper,
):
    """Test creating paper when it already exists."""
    # Setup extractor for test
    extractor_factory.register_extractor("arxiv", ArxivExtractor())

    mock_repo = mock_repo_class.return_value
    mock_repo.get_by_arxiv_id = AsyncMock(return_value=mock_paper)

    paper_data = PaperCreate(url="https://arxiv.org/abs/2508.01234")
    paper_creation_service = PaperCreationService()
    result = await paper_creation_service.create_paper(
        paper_data,
        mock_db_manager,
    )

    assert isinstance(result, PaperEntity)
    assert result.arxiv_id == "2508.01234"


@pytest.mark.asyncio
@patch("api.services.paper_creation_service.PaperRepository")
async def test_get_paper_by_identifier_arxiv_id(
    mock_repo_class,
    mock_db_manager,
    mock_paper,
):
    """Test getting paper by arXiv ID."""
    mock_repo = mock_repo_class.return_value
    mock_repo.get_by_arxiv_id = AsyncMock(return_value=mock_paper)

    paper_creation_service = PaperCreationService()
    result = await paper_creation_service.get_paper_by_identifier(
        "2508.01234", mock_db_manager
    )

    assert result == mock_paper


@pytest.mark.asyncio
@patch("api.services.paper_creation_service.PaperRepository")
async def test_get_paper_by_identifier_paper_id(
    mock_repo_class,
    mock_db_manager,
    mock_paper,
):
    """Test getting paper by paper ID."""
    mock_repo = mock_repo_class.return_value
    mock_repo.get_by_arxiv_id = AsyncMock(return_value=None)
    mock_repo.get_by_id = AsyncMock(return_value=mock_paper)

    paper_creation_service = PaperCreationService()
    result = await paper_creation_service.get_paper_by_identifier("1", mock_db_manager)

    assert result == mock_paper


@pytest.mark.asyncio
@patch("api.services.paper_creation_service.PaperRepository")
async def test_get_paper_by_identifier_not_found(
    mock_repo_class,
    mock_db_manager,
):
    """Test getting paper by identifier when not found."""
    mock_repo = mock_repo_class.return_value
    mock_repo.get_by_arxiv_id = AsyncMock(return_value=None)
    mock_repo.get_by_id = AsyncMock(return_value=None)

    paper_creation_service = PaperCreationService()
    result = await paper_creation_service.get_paper_by_identifier(
        "nonexistent",
        mock_db_manager,
    )

    assert result is None
