"""Integration tests for paper summary operations."""

import pytest
from fastapi.testclient import TestClient

from tests.integration.conftest import integration_client, parse_sse_events


class TestPaperSummaryIntegration:
    """Test paper summary operations with real database."""

    @pytest.mark.asyncio
    async def test_stream_paper_summary_basic_structure(
        self, integration_client: TestClient
    ):
        """Test streaming paper summary basic structure."""
        response = integration_client.post(
            "/v1/papers/stream-summary",
            json={
                "url": "https://arxiv.org/abs/1706.03762",
                "summary_language": "English",
            },
            headers={"Accept": "text/event-stream"},
        )

        assert response.status_code == 200
        assert response.headers["content-type"] == "text/event-stream; charset=utf-8"

        content = response.content.decode("utf-8")
        events = parse_sse_events(content)

        # Should have at least some events
        assert len(events) > 0

        # Check for complete event
        complete_events = [e for e in events if e.get("type") == "complete"]
        assert len(complete_events) > 0

    @pytest.mark.asyncio
    async def test_stream_paper_summary_with_summarization(
        self, integration_client: TestClient
    ):
        """Test streaming paper summary with actual summarization."""
        response = integration_client.post(
            "/v1/papers/stream-summary",
            json={
                "url": "https://arxiv.org/abs/1409.0575",
                "summary_language": "English",
            },
            headers={"Accept": "text/event-stream"},
        )

        assert response.status_code == 200

        content = response.content.decode("utf-8")
        events = parse_sse_events(content)

        # Should have complete event with paper data
        complete_events = [e for e in events if e.get("type") == "complete"]
        assert len(complete_events) > 0

        paper = complete_events[-1]["paper"]
        assert paper["arxiv_id"] == "1409.0575"
        assert paper["title"] is not None
        assert paper["paper_id"] is not None

    @pytest.mark.asyncio
    async def test_stream_paper_summary_invalid_url(
        self, integration_client: TestClient
    ):
        """Test streaming paper summary with invalid URL."""
        response = integration_client.post(
            "/v1/papers/stream-summary",
            json={
                "url": "https://invalid-url.com/paper",
                "summary_language": "English",
            },
            headers={"Accept": "text/event-stream"},
        )

        # Should still return streaming response even on error
        assert response.status_code == 200
        assert response.headers["content-type"] == "text/event-stream; charset=utf-8"

        content = response.content.decode("utf-8")
        events = parse_sse_events(content)

        # Should have error event
        error_events = [e for e in events if e.get("type") == "error"]
        assert len(error_events) > 0

    @pytest.mark.asyncio
    async def test_get_summary_success(self, integration_client: TestClient):
        """Test successful summary retrieval."""
        # First create a paper with summary
        response = integration_client.post(
            "/v1/papers/stream-summary",
            json={
                "url": "https://arxiv.org/abs/1409.0575",
                "summary_language": "English",
            },
            headers={"Accept": "text/event-stream"},
        )

        assert response.status_code == 200

        content = response.content.decode("utf-8")
        events = parse_sse_events(content)
        complete_events = [e for e in events if e.get("type") == "complete"]
        assert len(complete_events) > 0

        paper = complete_events[-1]["paper"]
        paper_id = paper["paper_id"]

        # Get summary
        response = integration_client.get(f"/v1/papers/{paper_id}/summary/1")

        assert response.status_code == 200
        data = response.json()
        assert data["paper_id"] == paper_id
        assert data["summary_id"] == 1
        assert data["overview"] is not None

    @pytest.mark.asyncio
    async def test_get_summary_not_found(self, integration_client: TestClient):
        """Test summary retrieval when summary not found."""
        response = integration_client.get("/v1/papers/1/summary/99999")

        assert response.status_code == 404

    @pytest.mark.asyncio
    async def test_mark_summary_as_read_success(self, integration_client: TestClient):
        """Test successful summary read marking."""
        # First create a paper with summary
        response = integration_client.post(
            "/v1/papers/stream-summary",
            json={
                "url": "https://arxiv.org/abs/1409.0575",
                "summary_language": "English",
            },
            headers={"Accept": "text/event-stream"},
        )

        assert response.status_code == 200

        content = response.content.decode("utf-8")
        events = parse_sse_events(content)
        complete_events = [e for e in events if e.get("type") == "complete"]
        assert len(complete_events) > 0

        paper = complete_events[-1]["paper"]
        paper_id = paper["paper_id"]

        # Mark summary as read
        response = integration_client.post(f"/v1/papers/{paper_id}/summary/1/read")

        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        assert data["is_read"] is True

    @pytest.mark.asyncio
    async def test_mark_summary_as_read_not_found(self, integration_client: TestClient):
        """Test summary read marking when summary not found."""
        response = integration_client.post("/v1/papers/1/summary/99999/read")

        assert response.status_code == 404
