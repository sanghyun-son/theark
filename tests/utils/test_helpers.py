"""Test helper utilities for theark tests."""

from typing import Any

from core.extractors.base import BaseExtractor
from core.extractors.concrete.arxiv_extractor import ArxivExtractor
from core.extractors.factory import register_extractor
from core.models.rows import Paper, Summary
from core.types import PaperSummaryStatus


class TestDataFactory:
    """Factory class for creating test data objects."""

    @staticmethod
    def create_test_paper(
        arxiv_id: str = "2508.01234",
        title: str = "Test Paper Title",
        abstract: str = "Test paper abstract",
        primary_category: str = "cs.AI",
        categories: str = "cs.AI,cs.LG",
        authors: str = "Author One;Author Two",
        summary_status: PaperSummaryStatus = PaperSummaryStatus.DONE,
        published_at: str = "2023-08-01T00:00:00Z",
    ) -> Paper:
        """Create a test Paper instance with default or custom values."""
        return Paper(
            arxiv_id=arxiv_id,
            title=title,
            abstract=abstract,
            primary_category=primary_category,
            categories=categories,
            authors=authors,
            url_abs=f"https://arxiv.org/abs/{arxiv_id}",
            url_pdf=f"https://arxiv.org/pdf/{arxiv_id}",
            published_at=published_at,
            summary_status=summary_status,
        )

    @staticmethod
    def create_test_summary(
        paper_id: int,
        version: str = "1.0",
        overview: str = "Test overview",
        motivation: str = "Test motivation",
        method: str = "Test method",
        result: str = "Test result",
        conclusion: str = "Test conclusion",
        language: str = "English",
        interests: str = "AI,ML",
        relevance: int = 8,
        model: str = "gpt-4",
    ) -> Summary:
        """Create a test Summary instance with default or custom values."""
        return Summary(
            summary_id=1,
            paper_id=paper_id,
            version=version,
            overview=overview,
            motivation=motivation,
            method=method,
            result=result,
            conclusion=conclusion,
            language=language,
            interests=interests,
            relevance=relevance,
            model=model,
        )


class TestSetupHelper:
    """Helper class for common test setup operations."""

    @staticmethod
    def register_test_extractors() -> None:
        """Register test extractors with common configuration."""
        # Clear any existing extractors
        from core.extractors.factory import _extractors

        _extractors.clear()

        # Register ArXiv extractor
        arxiv_extractor = ArxivExtractor()
        register_extractor("arxiv", arxiv_extractor)

    @staticmethod
    def register_mock_extractors(mock_extractor: BaseExtractor) -> None:
        """Register mock extractors for testing.

        Note: This should be used with the existing HTTP server-based mock fixtures
        from conftest.py (mock_arxiv_extractor, mock_openai_client) rather than
        creating new MagicMock instances.
        """
        # Clear any existing extractors
        from core.extractors.factory import _extractors

        _extractors.clear()

        # Register mock extractor
        register_extractor("arxiv", mock_extractor)

    @staticmethod
    def setup_paper_service_test(
        mock_arxiv_extractor: BaseExtractor,
        mock_openai_client: Any,
    ) -> None:
        """Setup common configuration for paper service tests.

        Args:
            mock_arxiv_extractor: Mock extractor from conftest.py fixture
            mock_openai_client: Mock OpenAI client from conftest.py fixture
        """
        TestSetupHelper.register_mock_extractors(mock_arxiv_extractor)

        # Additional setup can be added here as needed
        # For example, setting up mock responses, etc.


class AssertionHelper:
    """Helper class for common test assertions."""

    @staticmethod
    def assert_paper_response_valid(response: Any) -> None:
        """Assert that a paper response has valid structure."""
        assert response is not None
        assert hasattr(response, "arxiv_id")
        assert hasattr(response, "title")
        assert hasattr(response, "abstract")
        assert hasattr(response, "authors")
        assert hasattr(response, "primary_category")
        assert hasattr(response, "categories")
        assert hasattr(response, "url_abs")
        assert hasattr(response, "url_pdf")
        assert hasattr(response, "published_at")

    @staticmethod
    def assert_summary_valid(summary: Summary) -> None:
        """Assert that a summary has valid structure."""
        assert summary is not None
        assert summary.paper_id is not None
        assert summary.version is not None
        assert summary.overview is not None
        assert summary.motivation is not None
        assert summary.method is not None
        assert summary.result is not None
        assert summary.conclusion is not None
        assert summary.language is not None
        assert summary.interests is not None
        assert summary.relevance is not None
        assert summary.model is not None
