"""Tests for paper service."""

import pytest

from api.models.paper import PaperCreate, PaperDeleteResponse, PaperResponse
from api.services.paper_service import PaperService


class TestPaperService:
    """Test PaperService methods."""

    def setup_method(self) -> None:
        """Set up test fixtures."""
        self.service = PaperService()

    def test_extract_arxiv_id_from_arxiv_id(self) -> None:
        """Test extracting arXiv ID when arxiv_id is provided."""
        paper_data = PaperCreate(arxiv_id="2508.01234")
        arxiv_id = self.service._extract_arxiv_id(paper_data)
        assert arxiv_id == "2508.01234"

    def test_extract_arxiv_id_from_url(self) -> None:
        """Test extracting arXiv ID from URL."""
        paper_data = PaperCreate(url="https://arxiv.org/abs/2508.01234")
        arxiv_id = self.service._extract_arxiv_id(paper_data)
        assert arxiv_id == "2508.01234"

    def test_extract_arxiv_id_error_no_identifier(self) -> None:
        """Test error when no identifier is provided."""

        # Create a mock paper_data object to bypass validation
        class MockPaperData:
            def __init__(self):
                self.arxiv_id = None
                self.url = None

        paper_data = MockPaperData()
        with pytest.raises(ValueError, match="No arXiv ID or URL provided"):
            self.service._extract_arxiv_id(paper_data)

    @pytest.mark.asyncio
    async def test_create_paper_with_arxiv_id(self) -> None:
        """Test creating paper with arXiv ID."""
        paper_data = PaperCreate(arxiv_id="2508.01234")
        result = await self.service.create_paper(paper_data)

        assert isinstance(result, PaperResponse)
        assert result.arxiv_id == "2508.01234"
        assert result.title == "Placeholder Title"
        assert result.abstract == "Placeholder abstract"

    @pytest.mark.asyncio
    async def test_create_paper_with_url(self) -> None:
        """Test creating paper with URL."""
        paper_data = PaperCreate(url="https://arxiv.org/abs/2508.01234")
        result = await self.service.create_paper(paper_data)

        assert isinstance(result, PaperResponse)
        assert result.arxiv_id == "2508.01234"
        assert result.pdf_url == "https://arxiv.org/pdf/2508.01234"

    @pytest.mark.asyncio
    async def test_delete_paper(self) -> None:
        """Test deleting paper."""
        result = await self.service.delete_paper("2508.01234")

        assert isinstance(result, PaperDeleteResponse)
        assert result.id == "placeholder_id"
        assert result.arxiv_id == "placeholder_arxiv_id"
        assert "deleted successfully" in result.message
