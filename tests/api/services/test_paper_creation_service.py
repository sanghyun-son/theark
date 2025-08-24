"""Tests for paper creation service."""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from api.services.paper_creation_service import PaperCreationService
from core.models import PaperCreateRequest as PaperCreate
from core.models.database.entities import PaperEntity


class TestPaperCreationService:
    """Test PaperCreationService methods."""

    def setup_method(self) -> None:
        """Set up test fixtures."""
        self.mock_db_manager = MagicMock()
        self.mock_paper_repo = MagicMock()

        # Create service without database manager (DI pattern)
        self.service = PaperCreationService()

    def test_extract_arxiv_id_from_request(self) -> None:
        """Test extracting arXiv ID from request."""
        paper_data = PaperCreate(url="https://arxiv.org/abs/2508.01234")
        arxiv_id = self.service._extract_arxiv_id(paper_data)
        assert arxiv_id == "2508.01234"

    def test_extract_arxiv_id_error_no_identifier(self) -> None:
        """Test error when no identifier is provided."""

        class MockPaperData:
            def __init__(self):
                self.url = None

        paper_data = MockPaperData()
        with pytest.raises(ValueError, match="No URL provided"):
            self.service._extract_arxiv_id(paper_data)

    @pytest.mark.asyncio
    @patch("api.services.paper_creation_service.OnDemandCrawler")
    @patch("api.services.paper_creation_service.OnDemandCrawlConfig")
    @patch("api.services.paper_creation_service.PaperRepository")
    async def test_create_paper_new_paper(
        self, mock_repo_class, mock_config_class, mock_crawler_class
    ) -> None:
        """Test creating a new paper."""
        # Mock repository
        mock_repo_class.return_value = self.mock_paper_repo

        # Mock existing paper check
        self.mock_paper_repo.get_by_arxiv_id.return_value = None

        # Mock crawler
        mock_crawler = AsyncMock()
        mock_crawler.crawl_single_paper.return_value = self._create_mock_paper()
        mock_crawler_class.return_value.__aenter__.return_value = mock_crawler

        paper_data = PaperCreate(url="https://arxiv.org/abs/2508.01234")
        result = await self.service.create_paper(paper_data, self.mock_db_manager)

        assert isinstance(result, PaperEntity)
        assert result.arxiv_id == "2508.01234"
        assert result.title == "Test Paper Title"

    @pytest.mark.asyncio
    @patch("api.services.paper_creation_service.PaperRepository")
    async def test_create_paper_existing_paper(self, mock_repo_class) -> None:
        """Test creating paper when it already exists."""
        # Mock repository
        mock_repo_class.return_value = self.mock_paper_repo

        # Mock existing paper
        existing_paper = self._create_mock_paper()
        self.mock_paper_repo.get_by_arxiv_id.return_value = existing_paper

        paper_data = PaperCreate(url="https://arxiv.org/abs/2508.01234")
        result = await self.service.create_paper(paper_data, self.mock_db_manager)

        assert isinstance(result, PaperEntity)
        assert result.arxiv_id == "2508.01234"
        # Should return existing paper without crawling
        self.mock_paper_repo.get_by_arxiv_id.assert_called_once_with("2508.01234")

    @patch("api.services.paper_creation_service.PaperRepository")
    def test_get_paper_by_identifier_arxiv_id(self, mock_repo_class) -> None:
        """Test getting paper by arXiv ID."""
        # Mock repository
        mock_repo_class.return_value = self.mock_paper_repo

        mock_paper = self._create_mock_paper()
        self.mock_paper_repo.get_by_arxiv_id.return_value = mock_paper

        result = self.service.get_paper_by_identifier(
            "2508.01234", self.mock_db_manager
        )

        assert result == mock_paper
        self.mock_paper_repo.get_by_arxiv_id.assert_called_once_with("2508.01234")

    @patch("api.services.paper_creation_service.PaperRepository")
    def test_get_paper_by_identifier_paper_id(self, mock_repo_class) -> None:
        """Test getting paper by paper ID."""
        # Mock repository
        mock_repo_class.return_value = self.mock_paper_repo

        mock_paper = self._create_mock_paper()
        # Mock arXiv ID lookup to return None first, then paper ID lookup to return paper
        self.mock_paper_repo.get_by_arxiv_id.return_value = None
        self.mock_paper_repo.get_by_id.return_value = mock_paper

        result = self.service.get_paper_by_identifier("1", self.mock_db_manager)

        assert result == mock_paper
        self.mock_paper_repo.get_by_id.assert_called_once_with(1)

    @patch("api.services.paper_creation_service.PaperRepository")
    def test_get_paper_by_identifier_not_found(self, mock_repo_class) -> None:
        """Test getting paper by identifier when not found."""
        # Mock repository
        mock_repo_class.return_value = self.mock_paper_repo

        self.mock_paper_repo.get_by_arxiv_id.return_value = None
        self.mock_paper_repo.get_by_id.return_value = None

        result = self.service.get_paper_by_identifier(
            "nonexistent", self.mock_db_manager
        )

        assert result is None

    def _create_mock_paper(self) -> PaperEntity:
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
