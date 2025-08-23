"""Tests for paper service."""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch

from api.models.paper import PaperCreate, PaperDeleteResponse, PaperResponse
from api.services.paper_service import PaperService
from crawler.database import Paper as CrawlerPaper


class TestPaperService:
    """Test PaperService methods."""

    def setup_method(self) -> None:
        """Set up test fixtures."""
        # Create mock database manager
        self.mock_db_manager = AsyncMock()
        self.mock_paper_repo = MagicMock()  # Use MagicMock for sync methods
        self.mock_summary_repo = MagicMock()  # Use MagicMock for sync methods

        # Configure mock database manager
        self.mock_db_manager.get_paper_repository.return_value = self.mock_paper_repo
        self.mock_db_manager.get_summary_repository.return_value = (
            self.mock_summary_repo
        )

        # Create service with mock database manager
        self.service = PaperService(db_manager=self.mock_db_manager)

        # Mock summarization service
        self.service.summarization_service = AsyncMock()

        # Configure default mock behavior - ensure sync methods return actual values
        self.mock_paper_repo.get_by_arxiv_id.return_value = None

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
    @patch("api.services.paper_service.OnDemandCrawler")
    @patch("api.services.paper_service.OnDemandCrawlConfig")
    @patch("api.services.paper_service.PaperService._get_paper_by_arxiv_id")
    async def test_create_paper_with_arxiv_id(
        self, mock_get_paper, mock_config_class, mock_crawler_class
    ) -> None:
        """Test creating paper with arXiv ID."""
        # Mock existing paper check
        mock_get_paper.return_value = None

        # Mock crawler
        mock_crawler = AsyncMock()
        mock_crawler.crawl_single_paper.return_value = self._create_mock_crawler_paper()
        mock_crawler_class.return_value.__aenter__.return_value = mock_crawler

        paper_data = PaperCreate(arxiv_id="2508.01234")
        result = await self.service.create_paper(paper_data)

        assert isinstance(result, PaperResponse)
        assert result.arxiv_id == "2508.01234"
        assert result.title == "Test Paper Title"

    @pytest.mark.asyncio
    @patch("api.services.paper_service.OnDemandCrawler")
    @patch("api.services.paper_service.OnDemandCrawlConfig")
    @patch("api.services.paper_service.PaperService._get_paper_by_arxiv_id")
    async def test_create_paper_with_url(
        self, mock_get_paper, mock_config_class, mock_crawler_class
    ) -> None:
        """Test creating paper with URL."""
        # Mock existing paper check
        mock_get_paper.return_value = None

        # Mock crawler
        mock_crawler = AsyncMock()
        mock_crawler.crawl_single_paper.return_value = self._create_mock_crawler_paper()
        mock_crawler_class.return_value.__aenter__.return_value = mock_crawler

        paper_data = PaperCreate(url="https://arxiv.org/abs/2508.01234")
        result = await self.service.create_paper(paper_data)

        assert isinstance(result, PaperResponse)
        assert result.arxiv_id == "2508.01234"
        assert result.pdf_url == "https://arxiv.org/pdf/2508.01234"

    @pytest.mark.asyncio
    @patch("api.services.paper_service.PaperService._get_paper_by_arxiv_id")
    async def test_create_paper_existing_paper(self, mock_get_paper) -> None:
        """Test creating paper when it already exists."""
        # Mock existing paper
        existing_paper = self._create_mock_crawler_paper()

        # Mock the _get_paper_by_arxiv_id method directly
        mock_get_paper.return_value = existing_paper

        paper_data = PaperCreate(arxiv_id="2508.01234")
        result = await self.service.create_paper(paper_data)

        assert isinstance(result, PaperResponse)
        assert result.arxiv_id == "2508.01234"
        # Should return existing paper without crawling
        mock_get_paper.assert_called_once_with("2508.01234")

    @pytest.mark.asyncio
    @patch("api.services.paper_service.PaperService._get_paper_by_identifier")
    async def test_delete_paper(self, mock_get_paper) -> None:
        """Test deleting paper."""
        # Mock paper lookup
        mock_paper = self._create_mock_crawler_paper()
        mock_get_paper.return_value = mock_paper

        result = await self.service.delete_paper("2508.01234")

        assert isinstance(result, PaperDeleteResponse)
        assert result.id == "1"
        assert result.arxiv_id == "2508.01234"
        assert "deleted successfully" in result.message
        mock_get_paper.assert_called_once_with("2508.01234")

    @pytest.mark.asyncio
    @patch("api.services.paper_service.PaperService._get_paper_by_identifier")
    async def test_delete_paper_not_found(self, mock_get_paper) -> None:
        """Test deleting paper that doesn't exist."""
        # Mock paper not found
        mock_get_paper.return_value = None

        with pytest.raises(ValueError, match="Paper not found"):
            await self.service.delete_paper("2508.01234")

        mock_get_paper.assert_called_once_with("2508.01234")

    def _create_mock_crawler_paper(self) -> CrawlerPaper:
        """Create a mock CrawlerPaper for testing."""
        return CrawlerPaper(
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
