"""Tests for paper models."""

import pytest
from datetime import datetime
from pydantic import ValidationError

from api.models.paper import PaperCreate, PaperResponse
from crawler.database.models import Paper as CrawlerPaper


class TestPaperCreate:
    """Test PaperCreate model validation."""

    def test_valid_arxiv_id(self) -> None:
        """Test valid arXiv ID."""
        paper_data = PaperCreate(arxiv_id="2508.01234")
        assert paper_data.arxiv_id == "2508.01234"
        assert paper_data.url is None
        assert paper_data.summarize_now is True
        assert paper_data.force_refresh_metadata is False
        assert paper_data.force_resummarize is False

    def test_valid_url(self) -> None:
        """Test valid arXiv URL."""
        paper_data = PaperCreate(url="https://arxiv.org/abs/2508.01234")
        assert paper_data.url == "https://arxiv.org/abs/2508.01234"
        assert paper_data.arxiv_id is None
        assert paper_data.summarize_now is True

    def test_both_arxiv_id_and_url_matching(self) -> None:
        """Test when both arxiv_id and url are provided and match."""
        paper_data = PaperCreate(
            arxiv_id="2508.01234",
            url="https://arxiv.org/abs/2508.01234",
        )
        assert paper_data.arxiv_id == "2508.01234"
        assert paper_data.url == "https://arxiv.org/abs/2508.01234"

    def test_both_arxiv_id_and_url_conflict(self) -> None:
        """Test error when arxiv_id and url don't match."""
        with pytest.raises(ValidationError) as exc_info:
            PaperCreate(
                arxiv_id="2508.01234",
                url="https://arxiv.org/abs/2023.12345",
            )

        error = exc_info.value
        assert "arXiv ID and URL do not match" in str(error)

    def test_custom_flags(self) -> None:
        """Test custom flag values."""
        paper_data = PaperCreate(
            arxiv_id="2508.01234",
            summarize_now=False,
            force_refresh_metadata=True,
            force_resummarize=True,
        )
        assert paper_data.summarize_now is False
        assert paper_data.force_refresh_metadata is True
        assert paper_data.force_resummarize is True

    def test_missing_identifiers(self) -> None:
        """Test error when no identifier is provided."""
        with pytest.raises(ValidationError) as exc_info:
            PaperCreate()

        error = exc_info.value
        assert "Either arxiv_id or url must be provided" in str(error)

    def test_invalid_arxiv_id_format(self) -> None:
        """Test error with invalid arXiv ID format."""
        with pytest.raises(ValidationError) as exc_info:
            PaperCreate(arxiv_id="invalid")

        error = exc_info.value
        assert "Invalid arXiv ID format" in str(error)

    def test_invalid_url_format(self) -> None:
        """Test error with invalid URL format."""
        with pytest.raises(ValidationError) as exc_info:
            PaperCreate(url="https://example.com/paper")

        error = exc_info.value
        assert "Invalid arXiv URL format" in str(error)


class TestPaperResponse:
    """Test PaperResponse model."""

    def test_from_crawler_paper(self) -> None:
        """Test creating PaperResponse from CrawlerPaper."""
        crawler_paper = CrawlerPaper(
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

        response = PaperResponse.from_crawler_paper(
            crawler_paper, "Test summary"
        )

        assert response.id == "1"
        assert response.arxiv_id == "2508.01234"
        assert response.title == "Test Paper Title"
        assert response.abstract == "Test paper abstract"
        assert response.authors == ["Author One", "Author Two"]
        assert response.categories == ["cs.AI", "cs.LG"]
        assert response.pdf_url == "https://arxiv.org/pdf/2508.01234"
        assert response.summary == "Test summary"
        assert isinstance(response.published_date, datetime)
        assert isinstance(response.created_at, datetime)
        assert isinstance(response.updated_at, datetime)
