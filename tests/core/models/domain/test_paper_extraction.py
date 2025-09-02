"""Tests for paper extraction domain models."""

import pytest
from pydantic import ValidationError

from core.models.domain.paper_extraction import PaperMetadata


def test_create_paper_metadata_success() -> None:
    """Test successful PaperMetadata creation."""
    metadata = PaperMetadata(
        title="Test Paper",
        abstract="This is a test abstract",
        authors=["Author 1", "Author 2"],
        published_date="2023-01-01T00:00:00Z",
        updated_date="2023-01-02T00:00:00Z",
        url_abs="https://arxiv.org/abs/1234.5678",
    )

    assert metadata.title == "Test Paper"
    assert metadata.abstract == "This is a test abstract"
    assert metadata.authors == ["Author 1", "Author 2"]
    assert metadata.published_date == "2023-01-01T00:00:00Z"
    assert metadata.updated_date == "2023-01-02T00:00:00Z"
    assert metadata.url_abs == "https://arxiv.org/abs/1234.5678"
    assert metadata.url_pdf is None
    assert metadata.categories == []
    assert metadata.keywords == []
    assert metadata.raw_metadata == {}


def test_create_paper_metadata_with_optional_fields() -> None:
    """Test PaperMetadata creation with optional fields."""
    metadata = PaperMetadata(
        title="Test Paper",
        abstract="This is a test abstract",
        authors=["Author 1"],
        published_date="2023-01-01T00:00:00Z",
        updated_date="2023-01-02T00:00:00Z",
        url_abs="https://arxiv.org/abs/1234.5678",
        url_pdf="https://arxiv.org/pdf/1234.5678",
        categories=["cs.AI", "cs.LG"],
        keywords=["machine learning", "AI"],
        doi="10.1234/test.2023",
        journal="Test Journal",
        volume="1",
        pages="1-10",
        raw_metadata={"arxiv_id": "1234.5678"},
    )

    assert metadata.url_pdf == "https://arxiv.org/pdf/1234.5678"
    assert metadata.categories == ["cs.AI", "cs.LG"]
    assert metadata.keywords == ["machine learning", "AI"]
    assert metadata.doi == "10.1234/test.2023"
    assert metadata.journal == "Test Journal"
    assert metadata.volume == "1"
    assert metadata.pages == "1-10"
    assert metadata.raw_metadata == {"arxiv_id": "1234.5678"}


def test_create_paper_metadata_missing_required_fields() -> None:
    """Test PaperMetadata creation with missing required fields."""
    with pytest.raises(ValidationError):
        PaperMetadata(
            title="Test Paper",
            # Missing abstract
            authors=["Author 1"],
            published_date="2023-01-01T00:00:00Z",
            updated_date="2023-01-02T00:00:00Z",
            url_abs="https://arxiv.org/abs/1234.5678",
        )
