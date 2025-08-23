"""Tests for streaming service."""

import asyncio
import pytest
from unittest.mock import AsyncMock, MagicMock

from api.models.paper import PaperCreate, PaperResponse
from api.models.streaming import (
    StreamingStatusEvent,
    StreamingCompleteEvent,
    StreamingErrorEvent,
)
from api.services.streaming_service import StreamingService
from crawler.database.models import Paper


@pytest.fixture
def mock_paper_service():
    """Create mock paper service."""
    service = MagicMock()
    service.create_paper = AsyncMock()
    service.get_paper = AsyncMock()
    service._get_paper_by_identifier = MagicMock()
    service._summarize_paper_async = AsyncMock()
    return service


@pytest.fixture
def streaming_service(mock_paper_service):
    """Create streaming service with mocked dependencies."""
    return StreamingService(mock_paper_service)


@pytest.fixture
def sample_paper_data():
    """Sample paper creation data."""
    return PaperCreate(
        url="https://arxiv.org/abs/1706.02677",
        summarize_now=False,
        force_resummarize=False,
        summary_language="Korean",
    )


@pytest.fixture
def sample_paper_response():
    """Sample paper response."""
    return PaperResponse(
        paper_id=1,
        arxiv_id="1706.02677",
        title="Test Paper",
        authors=["Test Author"],
        abstract="Test abstract",
        categories=["cs.AI"],
        pdf_url="https://arxiv.org/pdf/1706.02677",
        published_date="2017-06-08",
    )


@pytest.fixture
def sample_paper():
    """Sample paper object."""
    paper = MagicMock(spec=Paper)
    paper.paper_id = 1
    paper.arxiv_id = "1706.02677"
    paper.title = "Test Paper"
    paper.authors = "Test Author"
    paper.abstract = "Test abstract"
    paper.categories = "cs.AI"
    paper.url_pdf = "https://arxiv.org/pdf/1706.02677"
    paper.published_at = "2017-06-08"
    return paper


class TestStreamingService:
    """Test streaming service functionality."""

    @pytest.mark.asyncio
    async def test_stream_paper_creation_no_summarization(
        self,
        streaming_service,
        mock_paper_service,
        sample_paper_data,
        sample_paper_response,
    ):
        """Test streaming paper creation without summarization."""
        # Mock service responses
        mock_paper_service.create_paper.return_value = sample_paper_response
        mock_paper_service._get_paper_by_identifier.return_value = None

        # Collect all events
        events = []
        async for event in streaming_service.stream_paper_creation(sample_paper_data):
            events.append(event)

        # Verify events - should get error when paper not found after creation
        assert len(events) == 3  # status + status + error
        assert "Creating paper..." in events[0]
        assert "Paper created successfully" in events[1]
        assert "error" in events[2]
        assert "Paper not found after creation" in events[2]

        # Verify service calls
        mock_paper_service.create_paper.assert_called_once_with(sample_paper_data)

    @pytest.mark.asyncio
    async def test_stream_paper_creation_no_summarization_success(
        self,
        streaming_service,
        mock_paper_service,
        sample_paper_data,
        sample_paper_response,
        sample_paper,
    ):
        """Test streaming paper creation without summarization when paper is found."""
        # Mock service responses
        mock_paper_service.create_paper.return_value = sample_paper_response
        mock_paper_service._get_paper_by_identifier.return_value = sample_paper

        # Collect all events
        events = []
        async for event in streaming_service.stream_paper_creation(sample_paper_data):
            events.append(event)

        # Verify events - should complete successfully without summarization
        assert len(events) == 3  # status + status + complete
        assert "Creating paper..." in events[0]
        assert "Paper created successfully" in events[1]
        assert "complete" in events[2]
        assert "1706.02677" in events[2]

        # Verify service calls
        mock_paper_service.create_paper.assert_called_once_with(sample_paper_data)

    @pytest.mark.asyncio
    async def test_stream_paper_creation_with_summarization(
        self,
        streaming_service,
        mock_paper_service,
        sample_paper_data,
        sample_paper_response,
        sample_paper,
    ):
        """Test streaming paper creation with summarization."""
        # Set up paper data to request summarization
        sample_paper_data.summarize_now = True

        # Mock service responses
        mock_paper_service.create_paper.return_value = sample_paper_response
        mock_paper_service._get_paper_by_identifier.return_value = sample_paper
        # Mock _summarize_paper_async to return a completed future
        mock_paper_service._summarize_paper_async.return_value = asyncio.Future()
        mock_paper_service._summarize_paper_async.return_value.set_result(None)
        mock_paper_service.get_paper.return_value = sample_paper_response

        # Collect all events
        events = []
        async for event in streaming_service.stream_paper_creation(sample_paper_data):
            events.append(event)

        # Debug: print actual events
        print(f"Actual events: {events}")

        # Verify events (should have more events due to summarization)
        assert len(events) >= 3  # status + status + complete
        assert "Creating paper..." in events[0]
        # Check if any event contains "Starting summarization..."
        summarization_started = any(
            "Starting summarization..." in event for event in events
        )
        assert (
            summarization_started
        ), f"Expected 'Starting summarization...' in events, got: {events}"
        assert "complete" in events[-1]

        # Verify service calls
        mock_paper_service.create_paper.assert_called_once_with(sample_paper_data)
        mock_paper_service._summarize_paper_async.assert_called_once()

    @pytest.mark.asyncio
    async def test_stream_paper_creation_error(
        self, streaming_service, mock_paper_service, sample_paper_data
    ):
        """Test streaming paper creation when service raises error."""
        # Mock service to raise error
        mock_paper_service.create_paper.side_effect = Exception("Service error")

        # Collect all events
        events = []
        async for event in streaming_service.stream_paper_creation(sample_paper_data):
            events.append(event)

        # Verify error event
        assert len(events) == 2  # status + error
        assert "Creating paper..." in events[0]
        assert "error" in events[1]
        assert "Service error" in events[1]

    def test_create_event(self, streaming_service):
        """Test event creation."""
        status_event = StreamingStatusEvent(message="Test message")
        event_str = streaming_service._create_event(status_event)

        assert event_str.startswith("data: ")
        assert "Test message" in event_str
        assert event_str.endswith("\n\n")

        complete_event = StreamingCompleteEvent(paper={"test": "data"})
        event_str = streaming_service._create_event(complete_event)

        assert "complete" in event_str
        assert "test" in event_str
