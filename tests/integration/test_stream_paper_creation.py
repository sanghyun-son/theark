"""Integration tests for streaming paper creation."""

import pytest
from fastapi.testclient import TestClient

from api.literals import (
    DEFAULT_SUMMARY_LANGUAGE,
    PAPERS_STREAM_SUMMARY_PATH,
    STREAMING_HEADERS,
    EventType,
    HTTPStatus,
)
from core.utils import parse_sse_events


@pytest.fixture
def valid_paper_request() -> dict:
    """Provide a valid paper creation request."""
    return {
        "url": "https://arxiv.org/abs/1409.0575",
        "summary_language": DEFAULT_SUMMARY_LANGUAGE,
    }


def test_summarize_stream_successful_response(
    integration_client: TestClient,
    valid_paper_request: dict,
) -> None:
    """Test that streaming paper creation returns successful HTTP response."""
    response = integration_client.post(
        PAPERS_STREAM_SUMMARY_PATH,
        json=valid_paper_request,
        headers=STREAMING_HEADERS,
    )

    assert response.status_code == HTTPStatus.OK
    assert response.headers["content-type"] == "text/event-stream; charset=utf-8"


def test_summarize_stream_events_structure(
    integration_client: TestClient,
    valid_paper_request: dict,
) -> None:
    """Test that streaming response contains expected event structure."""
    response = integration_client.post(
        PAPERS_STREAM_SUMMARY_PATH,
        json=valid_paper_request,
        headers=STREAMING_HEADERS,
    )

    content = response.content.decode("utf-8")
    events = parse_sse_events(content)

    assert len(events) > 0, "No events received"

    # Check for required event types
    status_events = [e for e in events if e.get("type") == EventType.STATUS]
    assert len(status_events) > 0, "No status events found"

    complete_events = [e for e in events if e.get("type") == EventType.COMPLETE]
    assert len(complete_events) > 0, "No complete event found"

    # Check for no error events
    error_events = [e for e in events if e.get("type") == EventType.ERROR]
    assert len(error_events) == 0, f"Unexpected error events: {error_events}"


def test_summarize_stream_paper_data_integrity(
    integration_client: TestClient,
    valid_paper_request: dict,
) -> None:
    """Test that final paper data contains expected information."""
    response = integration_client.post(
        PAPERS_STREAM_SUMMARY_PATH,
        json=valid_paper_request,
        headers=STREAMING_HEADERS,
    )

    content = response.content.decode("utf-8")
    events = parse_sse_events(content)

    complete_events = [e for e in events if e.get("type") == "complete"]
    assert len(complete_events) > 0, "No complete event found"

    # Verify paper data in the final complete event
    complete_event = complete_events[-1]
    assert "paper" in complete_event, "No paper data in complete event"

    paper = complete_event["paper"]
    assert paper["arxiv_id"] == "1409.0575"
    assert paper["title"] == "ImageNet Large Scale Visual Recognition Challenge"
    assert paper["summary"] is not None, "Paper summary should be generated"


def test_summarize_stream_no_database_connection_errors(
    integration_client: TestClient,
    valid_paper_request: dict,
) -> None:
    """Test that no database connection errors occur during streaming."""
    response = integration_client.post(
        PAPERS_STREAM_SUMMARY_PATH,
        json=valid_paper_request,
        headers=STREAMING_HEADERS,
    )

    content = response.content.decode("utf-8")
    events = parse_sse_events(content)

    # Verify no "Database not connected" errors
    error_events = [e for e in events if e.get("type") == EventType.ERROR]
    for error_event in error_events:
        message = error_event.get("message", "")
        assert (
            "Database not connected" not in message
        ), f"Found 'Database not connected' error: {message}"

    # Verify successful completion
    complete_events = [e for e in events if e.get("type") == EventType.COMPLETE]
    assert len(complete_events) > 0, "No complete event found - streaming failed"


def test_summarize_stream_with_different_language(
    integration_client: TestClient,
) -> None:
    """Test streaming paper creation with Korean language."""
    request = {
        "url": "https://arxiv.org/abs/1409.0575",
        "summary_language": "Korean",
    }

    response = integration_client.post(
        PAPERS_STREAM_SUMMARY_PATH,
        json=request,
        headers=STREAMING_HEADERS,
    )

    assert response.status_code == HTTPStatus.OK

    content = response.content.decode("utf-8")
    events = parse_sse_events(content)

    complete_events = [e for e in events if e.get("type") == EventType.COMPLETE]
    assert len(complete_events) > 0, "No complete event found"

    # Verify Korean summary was generated
    complete_event = complete_events[-1]
    paper = complete_event["paper"]
    assert paper["summary"] is not None, "Korean summary should be generated"


def test_summarize_stream_invalid_url(
    integration_client: TestClient,
) -> None:
    """Test streaming paper creation with invalid URL."""
    request = {
        "url": "https://invalid-url.com/paper",
        "summary_language": "English",
    }

    response = integration_client.post(
        PAPERS_STREAM_SUMMARY_PATH,
        json=request,
        headers=STREAMING_HEADERS,
    )

    # Should still return 200 for streaming, but with error events
    assert response.status_code == HTTPStatus.OK

    content = response.content.decode("utf-8")
    events = parse_sse_events(content)

    # Should have error events
    error_events = [e for e in events if e.get("type") == EventType.ERROR]
    assert len(error_events) > 0, "Should have error events for invalid URL"


def test_summarize_stream_events_sequence(
    integration_client: TestClient,
    valid_paper_request: dict,
) -> None:
    """Test that events follow expected sequence."""
    response = integration_client.post(
        PAPERS_STREAM_SUMMARY_PATH,
        json=valid_paper_request,
        headers=STREAMING_HEADERS,
    )

    content = response.content.decode("utf-8")
    events = parse_sse_events(content)

    # Verify event sequence: should start with status, end with complete
    assert len(events) >= 2, "Should have at least status and complete events"

    # First event should be status
    assert events[0].get("type") == EventType.STATUS, "First event should be status"

    # Last event should be complete
    assert events[-1].get("type") == EventType.COMPLETE, "Last event should be complete"

    # No error events in successful flow
    error_events = [e for e in events if e.get("type") == EventType.ERROR]
    assert len(error_events) == 0, "No error events should occur in successful flow"
