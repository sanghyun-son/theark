"""Tests for universal paper extractor."""

import pytest
from unittest.mock import Mock

from core.extractors.universal_extractor import UniversalPaperExtractor
from core.models.domain.paper_extraction import PaperMetadata


@pytest.fixture
def mock_extractor():
    """Mock paper extractor."""
    mock = Mock()
    mock.can_extract.return_value = True
    mock.extract_identifier.return_value = "test-id"
    mock.extract_metadata.return_value = Mock(spec=PaperMetadata)
    return mock


@pytest.fixture
def mock_arxiv_extractor():
    """Mock arXiv extractor."""
    mock = Mock()
    mock.can_extract.return_value = True
    mock.extract_identifier.return_value = "1234.5678"
    mock_metadata = PaperMetadata(
        title="Test Paper",
        abstract="Test abstract",
        authors=["Author 1"],
        published_date="2023-01-01T00:00:00Z",
        updated_date="2023-01-02T00:00:00Z",
        url_abs="https://arxiv.org/abs/1234.5678",
    )
    mock.extract_metadata.return_value = mock_metadata
    return mock


def test_extract_paper_success(mock_arxiv_extractor) -> None:
    """Test successful paper extraction."""
    extractor = UniversalPaperExtractor()

    # Replace the default ArxivExtractor with our mock
    extractor.extractors = [mock_arxiv_extractor]

    # Test extraction
    identifier, metadata = extractor.extract_paper("https://arxiv.org/abs/1234.5678")

    # Verify
    assert identifier == "1234.5678"
    assert metadata == mock_arxiv_extractor.extract_metadata.return_value
    mock_arxiv_extractor.can_extract.assert_called_once_with(
        "https://arxiv.org/abs/1234.5678"
    )
    mock_arxiv_extractor.extract_identifier.assert_called_once_with(
        "https://arxiv.org/abs/1234.5678"
    )
    mock_arxiv_extractor.extract_metadata.assert_called_once_with(
        "https://arxiv.org/abs/1234.5678"
    )


def test_extract_paper_no_extractor_found() -> None:
    """Test paper extraction when no extractor can handle the URL."""
    extractor = UniversalPaperExtractor()

    # Create a mock extractor that can't handle the URL
    mock_extractor = Mock()
    mock_extractor.can_extract.return_value = False

    # Replace the default ArxivExtractor with our mock
    extractor.extractors = [mock_extractor]

    # Test extraction
    with pytest.raises(ValueError, match="No extractor found for URL"):
        extractor.extract_paper("https://invalid-url.com/1234.5678")


def test_get_supported_sources() -> None:
    """Test getting supported sources."""
    extractor = UniversalPaperExtractor()

    # Create a mock extractor with source name
    mock_extractor = Mock()
    mock_extractor.get_source_name.return_value = "TestSource"

    # Replace the default ArxivExtractor with our mock
    extractor.extractors = [mock_extractor]

    # Test
    sources = extractor.get_supported_sources()

    # Verify
    assert sources == ["TestSource"]
