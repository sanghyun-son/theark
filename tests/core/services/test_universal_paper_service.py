"""Tests for universal paper service."""

import pytest
from unittest.mock import Mock, AsyncMock, patch

from core.services.universal_paper_service import UniversalPaperService
from core.models.domain.paper_source import PaperSource
from core.models.domain.paper_extraction import PaperMetadata
from core.models.database.entities import PaperEntity
from core.database.interfaces.manager import DatabaseManager


@pytest.fixture
def mock_extractor():
    """Mock UniversalPaperExtractor."""
    with patch(
        "core.services.universal_paper_service.UniversalPaperExtractor"
    ) as mock_class:
        mock_extractor = Mock()
        mock_class.return_value = mock_extractor
        yield mock_extractor


@pytest.fixture
def mock_repository():
    """Mock PaperRepository."""
    with patch("core.services.universal_paper_service.PaperRepository") as mock_class:
        mock_repo = Mock()
        mock_repo.create = AsyncMock(return_value=1)
        mock_repo.get_by_arxiv_id = AsyncMock()
        mock_class.return_value = mock_repo
        yield mock_repo


def test_determine_source_arxiv() -> None:
    """Test source determination for arXiv URLs."""
    service = UniversalPaperService()

    assert (
        service._determine_source("https://arxiv.org/abs/1234.5678")
        == PaperSource.ARXIV
    )
    assert (
        service._determine_source("https://arxiv.org/pdf/1234.5678")
        == PaperSource.ARXIV
    )


def test_determine_source_pubmed() -> None:
    """Test source determination for PubMed URLs."""
    service = UniversalPaperService()

    assert service._determine_source("https://pubmed.gov/12345") == PaperSource.PUBMED
    assert (
        service._determine_source("https://ncbi.nlm.nih.gov/pubmed/12345")
        == PaperSource.PUBMED
    )


def test_determine_source_ieee() -> None:
    """Test source determination for IEEE URLs."""
    service = UniversalPaperService()

    assert (
        service._determine_source("https://ieee.org/document/12345") == PaperSource.IEEE
    )
    assert (
        service._determine_source("https://ieeexplore.ieee.org/document/12345")
        == PaperSource.IEEE
    )


def test_determine_source_custom() -> None:
    """Test source determination for custom URLs."""
    service = UniversalPaperService()

    assert (
        service._determine_source("https://example.com/paper/123") == PaperSource.CUSTOM
    )


@pytest.mark.asyncio
async def test_create_paper_from_url_success(mock_extractor, mock_repository) -> None:
    """Test successful paper creation from URL."""
    # Mock metadata
    metadata = PaperMetadata(
        title="Test Paper",
        abstract="Test abstract",
        authors=["Author 1", "Author 2"],
        published_date="2023-01-01T00:00:00Z",
        updated_date="2023-01-02T00:00:00Z",
        url_abs="https://arxiv.org/abs/1234.5678",
        categories=["cs.AI", "cs.LG"],
    )

    mock_extractor.extract_paper.return_value = ("1234.5678", metadata)
    mock_repository.create.return_value = 1

    # Test
    service = UniversalPaperService()
    paper = await service.create_paper_from_url(
        "https://arxiv.org/abs/1234.5678",
        Mock(spec=DatabaseManager),
    )

    # Verify
    assert isinstance(paper, PaperEntity)
    assert paper.title == "Test Paper"
    assert paper.abstract == "Test abstract"
    assert paper.authors == "Author 1;Author 2"
    assert paper.primary_category == "cs.AI"
    assert paper.categories == "cs.AI,cs.LG"
    assert paper.paper_id == 1


@pytest.mark.asyncio
async def test_create_paper_from_url_with_default_category(
    mock_extractor, mock_repository
) -> None:
    """Test paper creation with default category when no categories provided."""
    # Mock metadata without categories
    metadata = PaperMetadata(
        title="Test Paper",
        abstract="Test abstract",
        authors=["Author 1"],
        published_date="2023-01-01T00:00:00Z",
        updated_date="2023-01-02T00:00:00Z",
        url_abs="https://arxiv.org/abs/1234.5678",
        categories=[],  # Empty categories
    )

    mock_extractor.extract_paper.return_value = ("1234.5678", metadata)
    mock_repository.create.return_value = 1

    # Test
    service = UniversalPaperService()
    paper = await service.create_paper_from_url(
        "https://arxiv.org/abs/1234.5678", Mock(spec=DatabaseManager)
    )

    # Verify default category is used
    assert paper.primary_category == "cs.OTHER"
    assert paper.categories == "cs.OTHER"


@pytest.mark.asyncio
async def test_create_paper_from_url_extraction_failure(mock_extractor) -> None:
    """Test paper creation when extraction fails."""
    mock_extractor.extract_paper.side_effect = ValueError("Extraction failed")

    # Test
    service = UniversalPaperService()

    with pytest.raises(ValueError, match="Extraction failed"):
        await service.create_paper_from_url(
            "https://arxiv.org/abs/1234.5678", Mock(spec=DatabaseManager)
        )


@pytest.mark.asyncio
async def test_get_paper_by_identifier_arxiv(mock_repository) -> None:
    """Test getting paper by arXiv identifier."""
    mock_paper = Mock(spec=PaperEntity)
    mock_repository.get_by_arxiv_id.return_value = mock_paper

    # Test
    service = UniversalPaperService()
    result = await service.get_paper_by_identifier(
        "1234.5678",
        Mock(spec=DatabaseManager),
    )

    # Verify
    assert result == mock_paper
    mock_repository.get_by_arxiv_id.assert_called_once_with("1234.5678")


@pytest.mark.asyncio
async def test_get_paper_by_identifier_source_format(mock_repository) -> None:
    """Test getting paper by source:identifier format."""
    mock_paper = Mock(spec=PaperEntity)
    mock_repository.get_by_arxiv_id.return_value = mock_paper

    # Test
    service = UniversalPaperService()
    result = await service.get_paper_by_identifier(
        "arxiv:1234.5678",
        Mock(spec=DatabaseManager),
    )

    # Verify
    assert result == mock_paper
    mock_repository.get_by_arxiv_id.assert_called_once_with("1234.5678")


@pytest.mark.asyncio
async def test_get_paper_by_identifier_not_found(mock_repository) -> None:
    """Test getting paper when not found."""
    mock_repository.get_by_arxiv_id.return_value = None

    # Test
    service = UniversalPaperService()
    result = await service.get_paper_by_identifier(
        "1234.5678",
        Mock(spec=DatabaseManager),
    )

    # Verify
    assert result is None
