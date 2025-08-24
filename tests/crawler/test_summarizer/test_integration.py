"""Integration tests for summarization with crawler."""

import os
from unittest.mock import AsyncMock, patch

import pytest
import pytest_asyncio

from crawler.arxiv.core import SummarizationConfig
from crawler.database import DatabaseManager
from crawler.summarizer.service import SummarizationService


class TestSummarizationIntegration:
    """Test summarization integration with crawler."""

    @pytest_asyncio.fixture
    async def mock_summarization_service(self):
        """Create a mock summarization service for testing."""
        with patch.dict(os.environ, {"OPENAI_API_KEY": "test-key"}):
            service = SummarizationService(
                api_key="test-key",
                base_url="http://localhost:12345",  # Mock server URL
                use_tools=True,
                model="gpt-4o-mini",
            )
            yield service
            await service.close()

    @pytest_asyncio.fixture
    async def db_manager(self, tmp_path):
        """Create a test database manager."""
        db_path = tmp_path / "test.db"
        manager = DatabaseManager(str(db_path))
        await manager.initialize()
        yield manager
        await manager.close()

    @pytest.mark.asyncio
    async def test_summarization_config_defaults(self):
        """Test that summarization config has correct defaults."""
        config = SummarizationConfig()

        assert config.summarize_immediately is False
        assert config.use_tools is True
        assert config.model == "gpt-4o-mini"
        assert config.language == "English"
        assert config.interest_section == "Machine Learning,Deep Learning"

    @pytest.mark.asyncio
    async def test_summarization_config_custom(self):
        """Test custom summarization config."""
        config = SummarizationConfig(
            summarize_immediately=True,
            use_tools=False,
            model="gpt-3.5-turbo",
            language="Spanish",
            interest_section="machine learning",
        )

        assert config.summarize_immediately is True
        assert config.use_tools is False
        assert config.model == "gpt-3.5-turbo"
        assert config.language == "Spanish"
        assert config.interest_section == "machine learning"

    @pytest.mark.asyncio
    async def test_summarization_service_initialization(self):
        """Test summarization service initialization."""
        with patch.dict(os.environ, {"OPENAI_API_KEY": "test-key"}):
            service = SummarizationService(
                api_key="test-key",
                base_url="http://localhost:12345",
                use_tools=True,
                model="gpt-4o-mini",
            )

            assert service.api_key == "test-key"
            assert service.base_url == "http://localhost:12345"
            assert service.use_tools is True
            assert service.model == "gpt-4o-mini"

            await service.close()

    @pytest.mark.asyncio
    async def test_summarization_service_missing_api_key(self):
        """Test that service raises error when API key is missing."""
        with patch.dict(os.environ, {}, clear=True):
            with pytest.raises(ValueError, match="OpenAI API key not provided"):
                SummarizationService()

    @pytest.mark.asyncio
    async def test_summarization_request_creation(self):
        """Test creating summarization requests."""
        from crawler.summarizer import SummaryRequest

        request = SummaryRequest(
            custom_id="test-paper-001",
            content="This is a test abstract about machine learning.",
            language="English",
            interest_section="AI and ML",
            use_tools=True,
            model="gpt-4o-mini",
        )

        assert request.custom_id == "test-paper-001"
        assert request.content == "This is a test abstract about machine learning."
        assert request.language == "English"
        assert request.interest_section == "AI and ML"
        assert request.use_tools is True
        assert request.model == "gpt-4o-mini"

    @pytest.mark.asyncio
    async def test_summarization_response_creation(self):
        """Test creating summarization responses."""
        from core.models.external.openai import PaperAnalysis
        from crawler.summarizer import SummaryResponse

        structured = PaperAnalysis(
            tldr="Test summary",
            motivation="Test motivation",
            method="Test method",
            result="Test result",
            conclusion="Test conclusion",
            relevance="High",
        )

        response = SummaryResponse(
            custom_id="test-paper-001",
            structured_summary=structured,
            original_length=100,
            summary_length=50,
            metadata={"model": "gpt-4o-mini"},
        )

        assert response.custom_id == "test-paper-001"
        assert response.structured_summary == structured
        assert response.original_length == 100
        assert response.summary_length == 50
        assert response.metadata["model"] == "gpt-4o-mini"
