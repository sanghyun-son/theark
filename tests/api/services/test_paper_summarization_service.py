"""Tests for paper summarization service."""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from api.services.paper_summarization_service import PaperSummarizationService
from core.models.database.entities import PaperEntity, SummaryEntity
from crawler.summarizer import SummaryResponse


class TestPaperSummarizationService:
    """Test PaperSummarizationService methods."""

    def setup_method(self) -> None:
        """Set up test fixtures."""
        self.mock_db_manager = MagicMock()
        self.mock_llm_db_manager = MagicMock()
        self.mock_summary_repo = MagicMock()

        # Create service without dependencies (DI pattern)
        self.service = PaperSummarizationService()

    @pytest.mark.asyncio
    @patch("api.services.paper_summarization_service.SummarizationService")
    @patch("api.services.paper_summarization_service.SummaryRepository")
    async def test_summarize_paper_success(
        self, mock_repo_class, mock_summarization_class
    ) -> None:
        """Test successful paper summarization."""
        # Mock repository and summarization service
        mock_repo_class.return_value = self.mock_summary_repo
        mock_summarization_service = AsyncMock()
        mock_summarization_service.summarize_paper = AsyncMock()
        mock_summarization_service.model = "gpt-4o-mini"
        mock_summarization_class.return_value = mock_summarization_service

        mock_paper = self._create_mock_paper()
        mock_summary_response = SummaryResponse(
            custom_id=mock_paper.arxiv_id,
            summary="Test summary text",
            structured_summary=None,
            original_length=100,
            summary_length=50,
        )

        # Mock summarization service response
        mock_summarization_service.summarize_paper.return_value = mock_summary_response

        # Mock no existing summary
        self.mock_summary_repo.get_by_paper_and_language.return_value = None

        # Mock summary creation
        self.mock_summary_repo.create.return_value = 1

        await self.service.summarize_paper(
            mock_paper, self.mock_db_manager, self.mock_llm_db_manager
        )

        # Verify summarization service was called
        mock_summarization_service.summarize_paper.assert_called_once_with(
            mock_paper.arxiv_id, mock_paper.abstract, language="Korean"
        )

        # Verify summary was saved
        self.mock_summary_repo.create.assert_called_once()

    @pytest.mark.asyncio
    @patch("api.services.paper_summarization_service.SummarizationService")
    @patch("api.services.paper_summarization_service.SummaryRepository")
    async def test_summarize_paper_existing_summary(
        self, mock_repo_class, mock_summarization_class
    ) -> None:
        """Test summarization when summary already exists."""
        # Mock repository and summarization service
        mock_repo_class.return_value = self.mock_summary_repo
        mock_summarization_service = AsyncMock()
        mock_summarization_class.return_value = mock_summarization_service

        mock_paper = self._create_mock_paper()
        existing_summary = self._create_mock_summary()

        # Mock existing summary
        self.mock_summary_repo.get_by_paper_and_language.return_value = existing_summary

        await self.service.summarize_paper(
            mock_paper, self.mock_db_manager, self.mock_llm_db_manager
        )

        # Verify summarization service was not called
        mock_summarization_service.summarize_paper.assert_not_called()

        # Verify summary was not saved
        self.mock_summary_repo.create.assert_not_called()

    @pytest.mark.asyncio
    @patch("api.services.paper_summarization_service.SummarizationService")
    @patch("api.services.paper_summarization_service.SummaryRepository")
    async def test_summarize_paper_force_resummarize(
        self, mock_repo_class, mock_summarization_class
    ) -> None:
        """Test summarization with force_resummarize=True."""
        # Mock repository and summarization service
        mock_repo_class.return_value = self.mock_summary_repo
        mock_summarization_service = AsyncMock()
        mock_summarization_service.summarize_paper = AsyncMock()
        mock_summarization_service.model = "gpt-4o-mini"
        mock_summarization_class.return_value = mock_summarization_service

        mock_paper = self._create_mock_paper()
        existing_summary = self._create_mock_summary()
        mock_summary_response = SummaryResponse(
            custom_id=mock_paper.arxiv_id,
            summary="New summary text",
            structured_summary=None,
            original_length=100,
            summary_length=50,
        )

        # Mock existing summary
        self.mock_summary_repo.get_by_paper_and_language.return_value = existing_summary

        # Mock summarization service response
        mock_summarization_service.summarize_paper.return_value = mock_summary_response

        # Mock summary creation
        self.mock_summary_repo.create.return_value = 1

        await self.service.summarize_paper(
            mock_paper,
            self.mock_db_manager,
            self.mock_llm_db_manager,
            force_resummarize=True,
        )

        # Verify summarization service was called despite existing summary
        mock_summarization_service.summarize_paper.assert_called_once_with(
            mock_paper.arxiv_id, mock_paper.abstract, language="Korean"
        )

        # Verify summary was saved
        self.mock_summary_repo.create.assert_called_once()

    @pytest.mark.asyncio
    async def test_summarize_paper_no_summarization_service(self) -> None:
        """Test summarization when summarization service is not available."""
        # This test is no longer relevant since we use DI pattern
        # Summarization service is always created when needed
        pass

    @patch("api.services.paper_summarization_service.SummaryRepository")
    def test_get_paper_summary_success(self, mock_repo_class) -> None:
        """Test getting paper summary successfully."""
        # Mock repository
        mock_repo_class.return_value = self.mock_summary_repo

        mock_paper = self._create_mock_paper()
        mock_summary = self._create_mock_summary()

        self.mock_summary_repo.get_by_paper_and_language.return_value = mock_summary

        result = self.service.get_paper_summary(mock_paper, self.mock_db_manager)

        assert result == mock_summary
        self.mock_summary_repo.get_by_paper_and_language.assert_called_once_with(
            mock_paper.paper_id, "Korean"
        )

    @patch("api.services.paper_summarization_service.SummaryRepository")
    def test_get_paper_summary_fallback_to_english(self, mock_repo_class) -> None:
        """Test getting paper summary with fallback to English."""
        # Mock repository
        mock_repo_class.return_value = self.mock_summary_repo

        mock_paper = self._create_mock_paper()
        mock_summary = self._create_mock_summary()

        # Mock no Korean summary, but English summary exists
        self.mock_summary_repo.get_by_paper_and_language.side_effect = [
            None,
            mock_summary,
        ]

        result = self.service.get_paper_summary(
            mock_paper, self.mock_db_manager, language="Korean"
        )

        assert result == mock_summary
        # Should have tried Korean first, then English
        assert self.mock_summary_repo.get_by_paper_and_language.call_count == 2

    @patch("api.services.paper_summarization_service.SummaryRepository")
    def test_get_paper_summary_not_found(self, mock_repo_class) -> None:
        """Test getting paper summary when not found."""
        # Mock repository
        mock_repo_class.return_value = self.mock_summary_repo

        mock_paper = self._create_mock_paper()

        self.mock_summary_repo.get_by_paper_and_language.return_value = None

        result = self.service.get_paper_summary(mock_paper, self.mock_db_manager)

        assert result is None

    def test_get_paper_summary_no_paper_id(self) -> None:
        """Test getting paper summary when paper has no ID."""
        mock_paper = self._create_mock_paper()
        mock_paper.paper_id = None

        result = self.service.get_paper_summary(mock_paper, self.mock_db_manager)

        assert result is None
        # No repository call should be made since paper_id is None

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

    def _create_mock_summary(self) -> SummaryEntity:
        """Create a mock SummaryEntity for testing."""
        return SummaryEntity(
            summary_id=1,
            paper_id=1,
            version=1,
            overview="Test overview",
            motivation="Test motivation",
            method="Test method",
            result="Test result",
            conclusion="Test conclusion",
            language="Korean",
            interests="machine learning",
            relevance=8,
            model="gpt-4o-mini",
            is_read=False,
            created_at="2023-08-01T00:00:00Z",
        )
