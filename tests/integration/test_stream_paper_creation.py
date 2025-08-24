"""Integration tests for streaming paper creation."""

import pytest
from fastapi.testclient import TestClient

from tests.integration.conftest import parse_sse_events


class TestStreamPaperCreationIntegration:
    """Integration tests for streaming paper creation functionality."""

    @pytest.mark.asyncio
    async def test_stream_paper_creation_end_to_end(
        self, integration_client: TestClient
    ):
        """Test end-to-end streaming paper creation with real database managers."""
        # Make streaming request
        response = integration_client.post(
            "/v1/papers/stream-summary",
            json={
                "url": "https://arxiv.org/abs/1409.0575",
                "summary_language": "English",
            },
            headers={"Accept": "text/event-stream"},
        )

        assert response.status_code == 200
        assert response.headers["content-type"] == "text/event-stream; charset=utf-8"

        # Parse streaming response
        content = response.content.decode("utf-8")
        events = parse_sse_events(content)

        # Verify events
        assert len(events) > 0, "No events received"

        # Check for status events
        status_events = [e for e in events if e.get("type") == "status"]
        assert len(status_events) > 0, "No status events found"

        # Check for complete event
        complete_events = [e for e in events if e.get("type") == "complete"]
        assert len(complete_events) > 0, "No complete event found"

        # Check for error events (should be none)
        error_events = [e for e in events if e.get("type") == "error"]
        assert len(error_events) == 0, f"Unexpected error events: {error_events}"

        # Print all events for debugging
        print(f"Total events received: {len(events)}")
        for i, event in enumerate(events):
            print(f"Event {i}: {event}")

        # Verify paper data in the final complete event (should have summary)
        complete_event = complete_events[-1]  # Get the last complete event
        assert "paper" in complete_event
        paper = complete_event["paper"]
        print(f"Final paper data: {paper}")
        assert paper["arxiv_id"] == "1409.0575"
        assert paper["title"] == "ImageNet Large Scale Visual Recognition Challenge"
        assert paper["summary"] is not None

    @pytest.mark.asyncio
    async def test_stream_paper_creation_database_connection(
        self, integration_client: TestClient
    ):
        """Test that no 'Database not connected' errors occur during streaming."""
        # Make streaming request
        response = integration_client.post(
            "/v1/papers/stream-summary",
            json={
                "url": "https://arxiv.org/abs/1409.0575",
                "summary_language": "English",
            },
            headers={"Accept": "text/event-stream"},
        )

        assert response.status_code == 200

        # Parse streaming response
        content = response.content.decode("utf-8")
        events = parse_sse_events(content)

        # Print events for debugging
        print(f"Total events received: {len(events)}")
        for i, event in enumerate(events):
            print(f"Event {i}: {event}")

        # Verify no "Database not connected" errors
        error_events = [e for e in events if e.get("type") == "error"]
        for error_event in error_events:
            message = error_event.get("message", "")
            assert (
                "Database not connected" not in message
            ), f"Found 'Database not connected' error: {message}"

        # Verify successful completion
        complete_events = [e for e in events if e.get("type") == "complete"]
        assert len(complete_events) > 0, "No complete event found - streaming failed"
