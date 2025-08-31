"""Tests for StreamService."""

import json
from unittest.mock import patch

import pytest
from sqlmodel import Session

from core.extractors.concrete import ArxivExtractor
from core.llm.openai_client import UnifiedOpenAIClient
from core.models import PaperCreateRequest
from core.models.api.responses import PaperResponse
from core.services.stream_service import StreamService


@pytest.fixture
def stream_service() -> StreamService:
    """Create StreamService instance."""
    return StreamService(default_interests=["Machine Learning"])


@pytest.fixture
def sample_paper_data() -> PaperCreateRequest:
    """Create sample paper request data."""
    return PaperCreateRequest(
        url="https://arxiv.org/abs/1706.03762",
        summary_language="English",
    )


@pytest.fixture
def sample_paper_response(saved_paper, saved_summary) -> PaperResponse:
    """Create sample paper response using existing fixtures."""
    # Create PaperResponse directly with the saved paper data
    return PaperResponse(
        paper_id=saved_paper.paper_id,
        arxiv_id=saved_paper.arxiv_id,
        title=saved_paper.title,
        abstract=saved_paper.abstract,
        primary_category=saved_paper.primary_category,
        categories=saved_paper.categories,
        authors=saved_paper.authors,
        url_abs=saved_paper.url_abs,
        url_pdf=saved_paper.url_pdf,
        published_at=saved_paper.published_at,
        summary_status=saved_paper.summary_status,
        latest_version=saved_paper.latest_version,
        updated_at=saved_paper.updated_at,
        summary=saved_summary,
        is_starred=False,
        is_read=False,
    )


@pytest.mark.asyncio
async def test_stream_paper_summarization_success(
    stream_service: StreamService,
    sample_paper_data: PaperCreateRequest,
    saved_paper,
    sample_paper_response: PaperResponse,
    saved_summary,
    mock_db_session: Session,
    mock_openai_client: UnifiedOpenAIClient,
    mock_arxiv_extractor: ArxivExtractor,
) -> None:
    """Test successful streaming paper summarization."""
    # Setup mocks
    with (
        patch.object(stream_service.paper_service, "create_paper") as mock_create,
        patch.object(
            stream_service.paper_service, "_get_paper_by_identifier"
        ) as mock_get_paper,
        patch.object(
            stream_service.summarization_service, "summarize_paper"
        ) as mock_summarize,
        patch.object(stream_service.paper_service, "get_paper") as mock_get_response,
    ):

        mock_create.return_value = sample_paper_response
        mock_get_paper.return_value = saved_paper
        mock_summarize.return_value = saved_summary
        mock_get_response.return_value = sample_paper_response

        # Execute
        events = []
        async for event in stream_service.stream_paper_summarization(
            sample_paper_data, mock_db_session, mock_openai_client
        ):
            events.append(event)

        # Assert
        assert len(events) == 5  # 4 status + 1 complete

        # Check status events
        status_events = [e for e in events if '"type": "status"' in e]
        assert len(status_events) == 4

        # Check that "Paper created successfully" status includes paper data
        paper_created_status = [
            e for e in status_events if '"message": "Paper created successfully"' in e
        ]
        assert len(paper_created_status) == 1
        paper_created_event = json.loads(
            paper_created_status[0].replace("data: ", "").strip()
        )
        assert "paper" in paper_created_event
        assert paper_created_event["paper"]["arxiv_id"] == "2101.00001"

        # Check complete event
        complete_events = [e for e in events if '"type": "complete"' in e]
        assert len(complete_events) == 1

        # Verify complete event contains paper data
        complete_event = json.loads(complete_events[0].replace("data: ", "").strip())
        assert complete_event["type"] == "complete"
        assert "paper" in complete_event
        assert complete_event["paper"]["arxiv_id"] == "2101.00001"


@pytest.mark.asyncio
async def test_stream_paper_summarization_paper_creation_failure(
    stream_service: StreamService,
    sample_paper_data: PaperCreateRequest,
    mock_db_session: Session,
    mock_openai_client: UnifiedOpenAIClient,
) -> None:
    """Test streaming when paper creation fails."""
    # Setup mock to fail
    with patch.object(stream_service.paper_service, "create_paper") as mock_create:
        mock_create.side_effect = ValueError("Failed to create paper")

        # Execute
        events = []
        async for event in stream_service.stream_paper_summarization(
            sample_paper_data, mock_db_session, mock_openai_client
        ):
            events.append(event)

        # Assert
        assert len(events) == 2  # 1 status + 1 error
        error_event = json.loads(events[-1].replace("data: ", "").strip())
        assert error_event["type"] == "error"
        assert "Failed to create paper" in error_event["message"]


@pytest.mark.asyncio
async def test_stream_paper_summarization_paper_not_found(
    stream_service: StreamService,
    sample_paper_data: PaperCreateRequest,
    sample_paper_response: PaperResponse,
    mock_db_session: Session,
    mock_openai_client: UnifiedOpenAIClient,
) -> None:
    """Test streaming when created paper cannot be retrieved."""
    # Setup mocks
    with (
        patch.object(stream_service.paper_service, "create_paper") as mock_create,
        patch.object(
            stream_service.paper_service, "_get_paper_by_identifier"
        ) as mock_get_paper,
    ):

        mock_create.return_value = sample_paper_response
        mock_get_paper.return_value = None  # Paper not found

        # Execute
        events = []
        async for event in stream_service.stream_paper_summarization(
            sample_paper_data, mock_db_session, mock_openai_client
        ):
            events.append(event)

        # Assert
        assert len(events) == 3  # 2 status events + 1 error
        error_event = json.loads(events[-1].replace("data: ", "").strip())
        assert error_event["type"] == "error"
        assert "Failed to retrieve created paper" in error_event["message"]


@pytest.mark.asyncio
async def test_stream_paper_summarization_summarization_skipped(
    stream_service: StreamService,
    sample_paper_data: PaperCreateRequest,
    saved_paper,
    sample_paper_response: PaperResponse,
    mock_db_session: Session,
    mock_openai_client: UnifiedOpenAIClient,
) -> None:
    """Test streaming when summarization is skipped (already exists)."""
    # Setup mocks
    with (
        patch.object(stream_service.paper_service, "create_paper") as mock_create,
        patch.object(
            stream_service.paper_service, "_get_paper_by_identifier"
        ) as mock_get_paper,
        patch.object(
            stream_service.summarization_service, "summarize_paper"
        ) as mock_summarize,
        patch.object(stream_service.paper_service, "get_paper") as mock_get_response,
    ):

        mock_create.return_value = sample_paper_response
        mock_get_paper.return_value = saved_paper
        mock_summarize.return_value = None  # Summary already exists
        mock_get_response.return_value = sample_paper_response

        # Execute
        events = []
        async for event in stream_service.stream_paper_summarization(
            sample_paper_data, mock_db_session, mock_openai_client
        ):
            events.append(event)

        # Assert
        assert len(events) == 5  # 4 status + 1 complete

        # Check for "skipped" message
        skipped_events = [e for e in events if "skipped" in e]
        assert len(skipped_events) == 1


@pytest.mark.asyncio
async def test_stream_paper_summarization_with_different_language(
    stream_service: StreamService,
    saved_paper,
    sample_paper_response: PaperResponse,
    saved_summary,
    mock_db_session: Session,
    mock_openai_client: UnifiedOpenAIClient,
) -> None:
    """Test streaming with Korean language."""
    # Setup Korean paper data
    korean_paper_data = PaperCreateRequest(
        url="https://arxiv.org/abs/1706.03762",
        summary_language="Korean",
    )

    # Setup mocks
    with (
        patch.object(stream_service.paper_service, "create_paper") as mock_create,
        patch.object(
            stream_service.paper_service, "_get_paper_by_identifier"
        ) as mock_get_paper,
        patch.object(
            stream_service.summarization_service, "summarize_paper"
        ) as mock_summarize,
        patch.object(stream_service.paper_service, "get_paper") as mock_get_response,
    ):

        mock_create.return_value = sample_paper_response
        mock_get_paper.return_value = saved_paper
        mock_summarize.return_value = saved_summary
        mock_get_response.return_value = sample_paper_response

        # Execute
        events = []
        async for event in stream_service.stream_paper_summarization(
            korean_paper_data, mock_db_session, mock_openai_client
        ):
            events.append(event)

        # Assert
        assert len(events) == 5  # 4 status + 1 complete

        # Verify Korean language was passed to summarization
        mock_summarize.assert_called_once()
        call_args = mock_summarize.call_args
        assert call_args[1]["language"] == "Korean"


@pytest.mark.asyncio
async def test_stream_paper_summarization_summarization_failure(
    stream_service: StreamService,
    sample_paper_data: PaperCreateRequest,
    saved_paper,
    sample_paper_response: PaperResponse,
    mock_db_session: Session,
    mock_openai_client: UnifiedOpenAIClient,
) -> None:
    """Test streaming when summarization fails."""
    # Setup mocks
    with (
        patch.object(stream_service.paper_service, "create_paper") as mock_create,
        patch.object(
            stream_service.paper_service, "_get_paper_by_identifier"
        ) as mock_get_paper,
        patch.object(
            stream_service.summarization_service, "summarize_paper"
        ) as mock_summarize,
    ):

        mock_create.return_value = sample_paper_response
        mock_get_paper.return_value = saved_paper
        mock_summarize.side_effect = Exception("Summarization failed")

        # Execute
        events = []
        async for event in stream_service.stream_paper_summarization(
            sample_paper_data, mock_db_session, mock_openai_client
        ):
            events.append(event)

        # Assert
        assert len(events) == 4  # 3 status events + 1 error
        error_event = json.loads(events[-1].replace("data: ", "").strip())
        assert error_event["type"] == "error"
        assert "Summarization failed" in error_event["message"]


@pytest.mark.asyncio
async def test_stream_paper_summarization_get_paper_failure(
    stream_service: StreamService,
    sample_paper_data: PaperCreateRequest,
    saved_paper,
    sample_paper_response: PaperResponse,
    saved_summary,
    mock_db_session: Session,
    mock_openai_client: UnifiedOpenAIClient,
) -> None:
    """Test streaming when final paper retrieval fails."""
    # Setup mocks
    with (
        patch.object(stream_service.paper_service, "create_paper") as mock_create,
        patch.object(
            stream_service.paper_service, "_get_paper_by_identifier"
        ) as mock_get_paper,
        patch.object(
            stream_service.summarization_service, "summarize_paper"
        ) as mock_summarize,
        patch.object(stream_service.paper_service, "get_paper") as mock_get_response,
    ):

        mock_create.return_value = sample_paper_response
        mock_get_paper.return_value = saved_paper
        mock_summarize.return_value = saved_summary
        mock_get_response.side_effect = Exception("Failed to get final paper")

        # Execute
        events = []
        async for event in stream_service.stream_paper_summarization(
            sample_paper_data, mock_db_session, mock_openai_client
        ):
            events.append(event)

        # Assert
        assert len(events) == 5  # 4 status events + 1 error
        error_event = json.loads(events[-1].replace("data: ", "").strip())
        assert error_event["type"] == "error"
        assert "Failed to get final paper" in error_event["message"]


def test_create_status_event(stream_service: StreamService) -> None:
    """Test status event creation."""
    event = stream_service._create_status_event("Test message")
    parsed_event = json.loads(event.replace("data: ", "").strip())

    assert parsed_event["type"] == "status"
    assert parsed_event["message"] == "Test message"
    assert "paper" not in parsed_event


def test_create_status_event_with_paper(
    stream_service: StreamService, sample_paper_response: PaperResponse
) -> None:
    """Test status event creation with paper data."""
    event = stream_service._create_status_event(
        "Paper created successfully", sample_paper_response
    )
    parsed_event = json.loads(event.replace("data: ", "").strip())

    assert parsed_event["type"] == "status"
    assert parsed_event["message"] == "Paper created successfully"
    assert "paper" in parsed_event
    assert parsed_event["paper"]["arxiv_id"] == "2101.00001"


def test_create_complete_event(
    stream_service: StreamService, sample_paper_response: PaperResponse
) -> None:
    """Test complete event creation."""
    event = stream_service._create_complete_event(sample_paper_response)
    parsed_event = json.loads(event.replace("data: ", "").strip())

    assert parsed_event["type"] == "complete"
    assert "paper" in parsed_event
    assert parsed_event["paper"]["arxiv_id"] == "2101.00001"


def test_create_error_event(stream_service: StreamService) -> None:
    """Test error event creation."""
    event = stream_service._create_error_event("Test error")
    parsed_event = json.loads(event.replace("data: ", "").strip())

    assert parsed_event["type"] == "error"
    assert parsed_event["message"] == "Test error"
