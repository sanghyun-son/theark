"""Tests for paper API models."""

import pytest
from pydantic import ValidationError

from api.models.paper import (
    PaperCreate,
    PaperDeleteResponse,
    PaperListRequest,
    PaperListResponse,
    PaperResponse,
    PaperSummary,
)


class TestPaperCreate:
    """Test PaperCreate model."""

    def test_valid_paper_create(self):
        """Test valid paper creation."""
        data = {
            "url": "https://arxiv.org/abs/2508.01234",
            "summarize_now": True,
            "summary_language": "Korean",
        }
        paper = PaperCreate(**data)
        assert paper.url == data["url"]
        assert paper.summarize_now is True
        assert paper.summary_language == "Korean"

    def test_invalid_summary_language(self):
        """Test invalid summary language."""
        data = {
            "url": "https://arxiv.org/abs/2508.01234",
            "summary_language": "Invalid",
        }
        with pytest.raises(ValidationError):
            PaperCreate(**data)

    def test_default_values(self):
        """Test default values."""
        data = {"url": "https://arxiv.org/abs/2508.01234"}
        paper = PaperCreate(**data)
        assert paper.summarize_now is False
        assert paper.force_refresh_metadata is False
        assert paper.force_resummarize is False
        assert paper.summary_language == "Korean"


class TestPaperListRequest:
    """Test PaperListRequest model."""

    def test_valid_request(self):
        """Test valid list request."""
        data = {"limit": 10, "offset": 5}
        request = PaperListRequest(**data)
        assert request.limit == 10
        assert request.offset == 5

    def test_default_values(self):
        """Test default values."""
        request = PaperListRequest()
        assert request.limit == 20
        assert request.offset == 0

    def test_limit_validation(self):
        """Test limit validation."""
        # Test minimum value
        with pytest.raises(ValidationError):
            PaperListRequest(limit=0)

        # Test maximum value
        with pytest.raises(ValidationError):
            PaperListRequest(limit=101)

    def test_offset_validation(self):
        """Test offset validation."""
        with pytest.raises(ValidationError):
            PaperListRequest(offset=-1)


class TestPaperListResponse:
    """Test PaperListResponse model."""

    def test_valid_response(self):
        """Test valid list response."""
        paper_data = {
            "paper_id": 1,
            "arxiv_id": "2508.01234",
            "title": "Test Paper",
            "authors": ["Author 1", "Author 2"],
            "abstract": "Test abstract",
            "categories": ["cs.AI"],
            "pdf_url": "https://arxiv.org/pdf/2508.01234",
        }
        data = {
            "papers": [paper_data],
            "total_count": 1,
            "limit": 20,
            "offset": 0,
            "has_more": False,
        }
        response = PaperListResponse(**data)
        assert response.total_count == 1
        assert response.limit == 20
        assert response.offset == 0
        assert response.has_more is False
        assert len(response.papers) == 1
        assert response.papers[0].paper_id == 1
        assert response.papers[0].arxiv_id == "2508.01234"

    def test_empty_papers(self):
        """Test response with empty papers list."""
        data = {
            "papers": [],
            "total_count": 0,
            "limit": 20,
            "offset": 0,
            "has_more": False,
        }
        response = PaperListResponse(**data)
        assert response.total_count == 0
        assert len(response.papers) == 0
        assert response.has_more is False


class TestPaperResponse:
    """Test PaperResponse model."""

    def test_valid_response(self):
        """Test valid paper response."""
        summary_data = {
            "overview": "Test summary",
            "motivation": "Test motivation",
            "relevance_score": 8,
        }
        data = {
            "paper_id": 1,
            "arxiv_id": "2508.01234",
            "title": "Test Paper",
            "authors": ["Author 1", "Author 2"],
            "abstract": "Test abstract",
            "categories": ["cs.AI"],
            "pdf_url": "https://arxiv.org/pdf/2508.01234",
            "published_date": "2025-01-01",
            "summary": summary_data,
        }
        response = PaperResponse(**data)
        assert response.paper_id == 1
        assert response.arxiv_id == "2508.01234"
        assert response.title == "Test Paper"
        assert response.authors == ["Author 1", "Author 2"]
        assert response.categories == ["cs.AI"]
        assert response.summary is not None
        assert response.summary.overview == "Test summary"
        assert response.summary.relevance_score == 8


class TestPaperSummary:
    """Test PaperSummary model."""

    def test_valid_summary(self):
        """Test valid summary data."""
        data = {
            "overview": "Test overview",
            "motivation": "Test motivation",
            "method": "Test method",
            "result": "Test result",
            "conclusion": "Test conclusion",
            "relevance": "High relevance",
            "relevance_score": 9,
        }
        summary = PaperSummary(**data)
        assert summary.overview == "Test overview"
        assert summary.motivation == "Test motivation"
        assert summary.relevance_score == 9

    def test_partial_summary(self):
        """Test summary with partial data."""
        data = {"overview": "Test overview", "relevance_score": 7}
        summary = PaperSummary(**data)
        assert summary.overview == "Test overview"
        assert summary.relevance_score == 7
        assert summary.motivation is None
        assert summary.method is None


class TestPaperDeleteResponse:
    """Test PaperDeleteResponse model."""

    def test_successful_deletion(self):
        """Test successful deletion response."""
        data = {"success": True, "message": "Paper deleted successfully"}
        response = PaperDeleteResponse(**data)
        assert response.success is True
        assert response.message == "Paper deleted successfully"

    def test_failed_deletion(self):
        """Test failed deletion response."""
        data = {"success": False, "message": "Paper not found"}
        response = PaperDeleteResponse(**data)
        assert response.success is False
        assert response.message == "Paper not found"
