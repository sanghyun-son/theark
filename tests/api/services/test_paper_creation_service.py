"""Tests for paper creation service."""

from unittest.mock import patch

import pytest

from api.services.paper_creation_service import PaperCreationService
from core.models import PaperCreateRequest as PaperCreate
from core.models.database.entities import PaperEntity


def test_extract_arxiv_id_from_request():
    """Test extracting arXiv ID from request."""
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
def paper_creation_service():
    """Create a PaperCreationService instance for testing."""
    return PaperCreationService()


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
    paper_creation_service,
    mock_sqlite_db,
    mock_arxiv_client,
    mock_paper,
):
    """Test creating a new paper."""
    # Mock repository
    mock_repo = mock_repo_class.return_value
    mock_repo.get_by_arxiv_id.return_value = None

    # Mock the crawler to return our mock paper
    async def mock_crawl_single_paper(identifier, db_manager, arxiv_client):
        return mock_paper

    # Override the service's _crawl_paper method
    paper_creation_service._crawl_paper = mock_crawl_single_paper

    paper_data = PaperCreate(url="https://arxiv.org/abs/2508.01234")
    result = await paper_creation_service.create_paper(
        paper_data, mock_sqlite_db, mock_arxiv_client
    )

    assert isinstance(result, PaperEntity)
    assert result.arxiv_id == "2508.01234"
    assert result.title == "Test Paper Title"


@pytest.mark.asyncio
@patch("api.services.paper_creation_service.PaperRepository")
async def test_create_paper_existing_paper(
    mock_repo_class,
    paper_creation_service,
    mock_sqlite_db,
    mock_arxiv_client,
    mock_paper,
):
    """Test creating paper when it already exists."""
    # Mock repository
    mock_repo = mock_repo_class.return_value
    mock_repo.get_by_arxiv_id.return_value = mock_paper

    paper_data = PaperCreate(url="https://arxiv.org/abs/2508.01234")
    result = await paper_creation_service.create_paper(
        paper_data, mock_sqlite_db, mock_arxiv_client
    )

    assert isinstance(result, PaperEntity)
    assert result.arxiv_id == "2508.01234"
    # Should return existing paper without crawling


@patch("api.services.paper_creation_service.PaperRepository")
def test_get_paper_by_identifier_arxiv_id(
    mock_repo_class, paper_creation_service, mock_sqlite_db, mock_paper
):
    """Test getting paper by arXiv ID."""
    mock_repo = mock_repo_class.return_value
    mock_repo.get_by_arxiv_id.return_value = mock_paper

    result = paper_creation_service.get_paper_by_identifier(
        "2508.01234", mock_sqlite_db
    )

    assert result == mock_paper


@patch("api.services.paper_creation_service.PaperRepository")
def test_get_paper_by_identifier_paper_id(
    mock_repo_class, paper_creation_service, mock_sqlite_db, mock_paper
):
    """Test getting paper by paper ID."""
    mock_repo = mock_repo_class.return_value
    # Mock arXiv ID lookup to return None first, then paper ID lookup to return paper
    mock_repo.get_by_arxiv_id.return_value = None
    mock_repo.get_by_id.return_value = mock_paper

    result = paper_creation_service.get_paper_by_identifier("1", mock_sqlite_db)

    assert result == mock_paper


@patch("api.services.paper_creation_service.PaperRepository")
def test_get_paper_by_identifier_not_found(
    mock_repo_class, paper_creation_service, mock_sqlite_db
):
    """Test getting paper by identifier when not found."""
    mock_repo = mock_repo_class.return_value
    mock_repo.get_by_arxiv_id.return_value = None
    mock_repo.get_by_id.return_value = None

    result = paper_creation_service.get_paper_by_identifier(
        "nonexistent", mock_sqlite_db
    )

    assert result is None
