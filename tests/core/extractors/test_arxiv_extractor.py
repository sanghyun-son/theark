"""Tests for ArXiv extractor."""

import pytest
from unittest.mock import AsyncMock, Mock, patch

from core.extractors.arxiv_extractor import ArxivExtractor
from core.models.domain.paper_extraction import PaperMetadata
from core.models.database.entities import PaperEntity


@pytest.fixture
def mock_arxiv_client():
    """Mock ArxivClient."""
    with patch("core.extractors.arxiv_extractor.ArxivClient") as mock_class:
        mock_client = Mock()
        mock_client.base_url = "http://export.arxiv.org/api/query"
        mock_class.return_value = mock_client
        yield mock_client


@pytest.fixture
def mock_arxiv_parser():
    """Mock ArxivParser."""
    with patch("core.extractors.arxiv_extractor.ArxivParser") as mock_class:
        mock_parser = Mock()
        mock_class.return_value = mock_parser
        yield mock_parser


def test_can_extract_arxiv_url() -> None:
    """Test can_extract with arXiv URL."""
    extractor = ArxivExtractor()

    assert extractor.can_extract("https://arxiv.org/abs/1234.5678")
    assert extractor.can_extract("https://arxiv.org/pdf/1234.5678")
    assert not extractor.can_extract("https://pubmed.gov/12345")


def test_extract_identifier_from_abs_url() -> None:
    """Test extract_identifier from abstract URL."""
    extractor = ArxivExtractor()

    identifier = extractor.extract_identifier("https://arxiv.org/abs/1234.5678")
    assert identifier == "1234.5678"


def test_extract_identifier_from_pdf_url() -> None:
    """Test extract_identifier from PDF URL."""
    extractor = ArxivExtractor()

    identifier = extractor.extract_identifier("https://arxiv.org/pdf/1234.5678")
    assert identifier == "1234.5678"


def test_extract_identifier_invalid_url() -> None:
    """Test extract_identifier with invalid URL."""
    extractor = ArxivExtractor()

    with pytest.raises(ValueError, match="Invalid arXiv URL format"):
        extractor.extract_identifier("https://invalid-url.com/1234.5678")


def test_extract_metadata_success(mock_arxiv_client, mock_arxiv_parser) -> None:
    """Test successful metadata extraction."""
    # Mock paper entity
    paper_entity = PaperEntity(
        arxiv_id="1234.5678",
        title="Test Paper",
        abstract="This is a test abstract",
        authors="Author 1;Author 2",
        primary_category="cs.AI",
        categories="cs.AI,cs.LG",
        url_abs="https://arxiv.org/abs/1234.5678",
        url_pdf="https://arxiv.org/pdf/1234.5678",
        published_at="2023-01-01T00:00:00Z",
        updated_at="2023-01-02T00:00:00Z",
    )

    mock_arxiv_parser.parse_paper.return_value = paper_entity
    mock_arxiv_client.get_paper = AsyncMock(return_value="<xml>test</xml>")

    # Test
    extractor = ArxivExtractor()
    metadata = extractor.extract_metadata("https://arxiv.org/abs/1234.5678")

    # Verify
    assert isinstance(metadata, PaperMetadata)
    assert metadata.title == "Test Paper"
    assert metadata.abstract == "This is a test abstract"
    assert metadata.authors == ["Author 1", "Author 2"]
    assert metadata.categories == ["cs.AI", "cs.LG"]
    assert metadata.url_abs == "https://arxiv.org/abs/1234.5678"
    assert metadata.url_pdf == "https://arxiv.org/pdf/1234.5678"
    assert metadata.raw_metadata == {"arxiv_id": "1234.5678"}


def test_extract_metadata_parse_failure(mock_arxiv_client, mock_arxiv_parser) -> None:
    """Test metadata extraction when parsing fails."""
    mock_arxiv_parser.parse_paper.return_value = None
    mock_arxiv_client.get_paper = AsyncMock(return_value="<xml>test</xml>")

    # Test
    extractor = ArxivExtractor()

    with pytest.raises(ValueError, match="Failed to parse arXiv paper"):
        extractor.extract_metadata("https://arxiv.org/abs/1234.5678")
