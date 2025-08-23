"""Tests for the summarizer module structure."""

import pytest

from core.models.external.openai import PaperAnalysis
from crawler.summarizer.summarizer import (
    AbstractSummarizer,
    SummaryRequest,
    SummaryResponse,
)


class TestSummaryRequest:
    """Test SummaryRequest dataclass."""

    def test_summary_request_creation(self):
        """Test creating a SummaryRequest with default values."""
        request = SummaryRequest(custom_id="test-001", content="Test abstract")
        assert request.custom_id == "test-001"
        assert request.content == "Test abstract"
        assert request.language == "English"
        assert request.interest_section == ""
        assert request.use_tools is True
        assert request.model == "gpt-4o-mini"

    def test_summary_request_custom_values(self):
        """Test creating a SummaryRequest with custom values."""
        request = SummaryRequest(
            custom_id="test-002",
            content="Test abstract",
            language="Spanish",
            interest_section="machine learning",
            use_tools=False,
            model="gpt-4",
        )
        assert request.custom_id == "test-002"
        assert request.content == "Test abstract"
        assert request.language == "Spanish"
        assert request.interest_section == "machine learning"
        assert request.use_tools is False
        assert request.model == "gpt-4"


class TestSummaryResponse:
    """Test SummaryResponse dataclass."""

    def test_summary_response_creation(self):
        """Test creating a SummaryResponse with text summary."""
        response = SummaryResponse(
            custom_id="test-001",
            summary="Test summary",
            original_length=100,
            summary_length=50,
        )
        assert response.custom_id == "test-001"
        assert response.summary == "Test summary"
        assert response.structured_summary is None
        assert response.original_length == 100
        assert response.summary_length == 50
        assert response.metadata is None

    def test_summary_response_with_structured_summary(self):
        """Test creating a SummaryResponse with structured summary."""
        structured = PaperAnalysis(
            tldr="Short summary",
            motivation="Research motivation",
            method="Proposed method",
            result="Experimental results",
            conclusion="Main conclusion",
            relevance="High",
        )
        response = SummaryResponse(
            custom_id="test-002",
            structured_summary=structured,
            original_length=200,
            summary_length=150,
        )
        assert response.custom_id == "test-002"
        assert response.summary is None
        assert response.structured_summary == structured
        assert response.original_length == 200
        assert response.summary_length == 150

    def test_summary_response_with_metadata(self):
        """Test creating a SummaryResponse with metadata."""
        metadata = {"model": "gpt-4o-mini", "tokens": 150}
        response = SummaryResponse(
            custom_id="test-003",
            summary="Test summary",
            metadata=metadata,
        )
        assert response.custom_id == "test-003"
        assert response.metadata == metadata


class TestPaperAnalysis:
    """Test PaperAnalysis model."""

    def test_paper_analysis_creation(self):
        """Test creating a PaperAnalysis."""
        structured = PaperAnalysis(
            tldr="Brief summary",
            motivation="Paper motivation",
            method="Research method",
            result="Key results",
            conclusion="Main conclusion",
            relevance="High",
        )
        assert structured.tldr == "Brief summary"
        assert structured.motivation == "Paper motivation"
        assert structured.method == "Research method"
        assert structured.result == "Key results"
        assert structured.conclusion == "Main conclusion"
        assert structured.relevance == "High"


class TestAbstractSummarizer:
    """Test AbstractSummarizer base class."""

    def test_abstract_summarizer_is_abstract(self):
        """Test that AbstractSummarizer cannot be instantiated."""
        with pytest.raises(TypeError):
            AbstractSummarizer()

    def test_abstract_summarizer_has_summarize_method(self):
        """Test that AbstractSummarizer has the required abstract method."""
        assert hasattr(AbstractSummarizer, "summarize")
        assert AbstractSummarizer.summarize.__isabstractmethod__
