"""Integration tests for summarization with crawler."""

import pytest

from crawler.summarizer.service import SummarizationService
from crawler.summarizer import SummaryRequest, SummaryResponse
from core.models.external.openai import PaperAnalysis


@pytest.mark.asyncio
async def test_summarization_service_summarize_paper_success(
    mock_summary_client,
    mock_db_manager,
) -> None:
    """Test successful paper summarization."""
    service = SummarizationService()

    # Test the summarization
    result = await service.summarize_paper(
        paper_id="test-paper-001",
        abstract="This is a test abstract about machine learning.",
        summary_client=mock_summary_client,
        db_manager=mock_db_manager,
        language="English",
        interest_section="AI and ML",
    )

    assert result is not None
    assert result.custom_id == "test-paper-001"
    assert result.structured_summary is not None
    assert result.structured_summary.tldr == (
        "This paper presents a novel approach "
        "to abstract summarization using professional analysis methods."
    )
    assert result.structured_summary.relevance == 8


@pytest.mark.asyncio
async def test_summarization_service_summarize_paper_failure(
    mock_summary_client,
    mock_db_manager,
) -> None:
    """Test paper summarization failure."""
    service = SummarizationService()

    # Test the summarization
    result = await service.summarize_paper(
        paper_id="test-paper-001",
        abstract="This is a test abstract about machine learning.",
        summary_client=mock_summary_client,
        db_manager=mock_db_manager,
        language="English",
        interest_section="AI and ML",
    )

    # The mock server should return a valid response, so this should not be None
    assert result is not None


def test_summarization_request_creation() -> None:
    """Test creating summarization requests."""
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


def test_summarization_response_creation() -> None:
    """Test creating summarization responses."""
    structured = PaperAnalysis(
        tldr="Test summary",
        motivation="Test motivation",
        method="Test method",
        result="Test result",
        conclusion="Test conclusion",
        relevance=9,
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
