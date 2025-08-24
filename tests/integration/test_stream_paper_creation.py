"""Integration tests for streaming paper creation."""

import json
import os
from pathlib import Path
from unittest.mock import patch

import pytest
from fastapi.testclient import TestClient

from api.app import create_app
from crawler.database import LLMSQLiteManager
from crawler.database.sqlite_manager import SQLiteManager
from core.types import Environment


class TestStreamPaperCreationIntegration:
    """Integration tests for streaming paper creation functionality."""

    @pytest.fixture
    def client(
        self, tmp_path: Path, mock_arxiv_server, mock_openai_server
    ) -> TestClient:
        """Create a test client with real database managers using mock servers."""
        # Set environment variables for testing
        test_env = {
            "THEARK_ENV": "testing",
            "THEARK_ARXIV_API_BASE_URL": f"http://{mock_arxiv_server.host}:{mock_arxiv_server.port}",
            "THEARK_LLM_API_BASE_URL": f"http://{mock_openai_server.host}:{mock_openai_server.port}",
            "OPENAI_API_KEY": "test-api-key",
            "THEARK_LOG_LEVEL": "DEBUG",
        }

        with patch.dict(os.environ, test_env, clear=False):
            # Create app - it will automatically detect testing environment and use temp DB paths
            app = create_app()

            # Manually initialize app state since lifespan might not run in tests
            from api.services.paper_service import PaperService
            from crawler.arxiv.client import ArxivClient

            # Create ArxivClient with mock server URL
            mock_arxiv_base_url = (
                f"http://{mock_arxiv_server.host}:{mock_arxiv_server.port}/api/query"
            )
            arxiv_client = ArxivClient(base_url=mock_arxiv_base_url)

            # Use tmp_path for testing databases
            db_path = tmp_path / "test.db"
            db_manager = SQLiteManager(db_path)
            db_manager.connect()
            db_manager.create_tables()

            llm_db_path = tmp_path / "test_llm.db"
            llm_db_manager = LLMSQLiteManager(llm_db_path)
            llm_db_manager.connect()
            llm_db_manager.create_tables()

            app.state.db_manager = db_manager
            app.state.llm_db_manager = llm_db_manager
            app.state.paper_service = PaperService()
            app.state.arxiv_client = arxiv_client

            return TestClient(app)

    @pytest.mark.asyncio
    async def test_stream_paper_creation_end_to_end(self, client: TestClient):
        """Test end-to-end streaming paper creation with real database managers."""
        # Make streaming request
        response = client.post(
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
        events = []
        for line in content.strip().split("\n"):
            if line.startswith("data: "):
                event_data = line[6:]  # Remove "data: " prefix
                if event_data.strip():
                    try:
                        event = json.loads(event_data)
                        events.append(event)
                    except json.JSONDecodeError:
                        continue

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
    async def test_stream_paper_creation_database_connection(self, client: TestClient):
        """Test that no 'Database not connected' errors occur during streaming."""
        # Make streaming request
        response = client.post(
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
        events = []
        for line in content.strip().split("\n"):
            if line.startswith("data: "):
                event_data = line[6:]  # Remove "data: " prefix
                if event_data.strip():
                    try:
                        event = json.loads(event_data)
                        events.append(event)
                    except json.JSONDecodeError:
                        continue

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
