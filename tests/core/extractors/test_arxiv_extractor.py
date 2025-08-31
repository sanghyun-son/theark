"""Tests for ArXiv extractor."""

import pytest

from core.extractors.concrete.arxiv_extractor import ArxivExtractor
from core.extractors.exceptions import ExtractionError, InvalidIdentifierError
from core.models.domain.paper_extraction import PaperMetadata


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


def test_extract_identifier_from_direct_id() -> None:
    """Test extract_identifier from direct arXiv ID."""
    extractor = ArxivExtractor()

    identifier = extractor.extract_identifier("1234.5678")
    assert identifier == "1234.5678"


def test_extract_identifier_from_versioned_url() -> None:
    """Test extract_identifier from versioned URL."""
    extractor = ArxivExtractor()

    identifier = extractor.extract_identifier("https://arxiv.org/abs/1234.5678v2")
    assert identifier == "1234.5678"


def test_extract_identifier_invalid_url() -> None:
    """Test extract_identifier with invalid URL."""
    extractor = ArxivExtractor()

    with pytest.raises(InvalidIdentifierError, match="Could not extract arXiv ID"):
        extractor.extract_identifier("https://invalid-url.com/1234.5678")


@pytest.mark.asyncio
async def test_extract_metadata_success(mock_arxiv_extractor) -> None:
    """Test successful metadata extraction."""
    # Test with a known paper ID
    metadata = await mock_arxiv_extractor.extract_metadata_async(
        "https://arxiv.org/abs/1706.03762"
    )

    # Verify basic structure
    assert isinstance(metadata, PaperMetadata)
    assert metadata.title
    assert metadata.abstract
    assert metadata.authors
    assert metadata.url_abs == "https://arxiv.org/abs/1706.03762"
    assert metadata.url_pdf == "https://arxiv.org/pdf/1706.03762"
    assert metadata.raw_metadata["arxiv_id"] == "1706.03762"


@pytest.mark.asyncio
async def test_extract_metadata_network_error() -> None:
    """Test metadata extraction with network error."""
    # Create extractor with invalid URL
    extractor = ArxivExtractor(api_base_url="http://invalid-server.com/api/query")

    with pytest.raises(ExtractionError, match="Network error"):
        await extractor.extract_metadata_async("https://arxiv.org/abs/1706.03762")


@pytest.mark.asyncio
async def test_extract_metadata_server_error(mock_arxiv_extractor) -> None:
    """Test metadata extraction with server error."""
    # Test with a paper ID that returns server error
    with pytest.raises(ExtractionError, match="HTTP error"):
        await mock_arxiv_extractor.extract_metadata_async(
            "https://arxiv.org/abs/1706.99999"
        )


@pytest.mark.asyncio
async def test_extract_metadata_with_mock_response(mock_arxiv_extractor) -> None:
    """Test metadata extraction using the mock response."""
    # Test with a paper ID from our example XML
    metadata = await mock_arxiv_extractor.extract_metadata_async("2501.00961v3")

    # Check that we got a PaperMetadata with the expected fields
    assert metadata.title == "ImageNet Large Scale Visual Recognition Challenge"
    assert "cs.CV" in metadata.categories
    assert metadata.raw_metadata["arxiv_id"] == "2501.00961"


def test_get_source_name() -> None:
    """Test get_source_name method."""
    extractor = ArxivExtractor()
    assert extractor.get_source_name() == "Arxiv"


def test_custom_base_urls() -> None:
    """Test extractor with custom base URLs."""
    extractor = ArxivExtractor(
        api_base_url="https://custom-api.example.com/query",
        abs_base_url="https://custom-abs.example.com",
        pdf_base_url="https://custom-pdf.example.com",
    )

    assert extractor.base_url == "https://custom-api.example.com/query"
    assert extractor.abs_base_url == "https://custom-abs.example.com"
    assert extractor.pdf_base_url == "https://custom-pdf.example.com"
