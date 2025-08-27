"""Common fixtures for integration tests."""

import json
import os
from typing import AsyncGenerator
from pathlib import Path
from unittest.mock import patch

import pytest_asyncio
from fastapi.testclient import TestClient

from api.app import create_app
from core.batch.background_manager import BackgroundBatchManager
from core.database.implementations.sqlite.sqlite_manager import SQLiteManager
from core.llm.openai_client import UnifiedOpenAIClient


@pytest_asyncio.fixture
async def integration_client(
    tmp_path: Path,
    mock_arxiv_extractor,
    mock_openai_client: UnifiedOpenAIClient,
) -> AsyncGenerator[TestClient, None]:
    """Create a test client with real database managers using mock servers."""
    # Set up URLs first

    # Set environment variables for testing
    test_env = {"THEARK_ENV": "testing", "THEARK_LOG_LEVEL": "DEBUG"}

    with patch.dict(os.environ, test_env, clear=True):
        # Force reload settings with new environment variables
        from core import config
        from core.extractors import extractor_factory

        config.settings = config.load_settings()

        # Create app - it will automatically detect testing environment and use temp DB paths
        app = create_app()

        app.state.db_manager = SQLiteManager(tmp_path / "test.db")
        await app.state.db_manager.connect()
        await app.state.db_manager.create_tables()

        extractor_factory.register_extractor(
            "arxiv",
            mock_arxiv_extractor,
        )
        app.state.summary_client = mock_openai_client

        # Set up background batch manager for integration tests
        app.state.background_batch_manager = BackgroundBatchManager(config.settings)
        app.state.openai_batch_client = mock_openai_client
        # Start the background manager with the mock OpenAI client
        await app.state.background_batch_manager.start(
            app.state.db_manager, mock_openai_client
        )

        yield TestClient(app)

        # Stop the background manager
        await app.state.background_batch_manager.stop()
        await app.state.db_manager.disconnect()


def parse_sse_events(content: str) -> list[dict]:
    """Parse Server-Sent Events content into list of events."""
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
    return events
