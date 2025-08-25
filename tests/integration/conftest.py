"""Common fixtures for integration tests."""

import json
import os
from pathlib import Path
from unittest.mock import patch

import pytest
from pytest_httpserver import HTTPServer
from fastapi.testclient import TestClient

from api.app import create_app
from core.database.llm_sqlite_manager import LLMSQLiteManager
from core.database.sqlite_manager import SQLiteManager
from core.database.repository import UserRepository
from core.models.domain.user import DEFAULT_USER_ID


@pytest.fixture
def integration_client(
    tmp_path: Path,
    mock_arxiv_server: HTTPServer,
    mock_openai_server: HTTPServer,
) -> TestClient:
    """Create a test client with real database managers using mock servers."""
    # Set up URLs first
    arxiv_url = f"http://{mock_arxiv_server.host}:{mock_arxiv_server.port}/api/query"
    openai_url = f"http://{mock_openai_server.host}:{mock_openai_server.port}/v1"

    # Set environment variables for testing
    test_env = {
        "THEARK_ENV": "testing",
        "THEARK_ARXIV_API_BASE_URL": arxiv_url,
        "THEARK_LLM_API_BASE_URL": openai_url,
        "OPENAI_API_KEY": "test-api-key",
        "THEARK_LOG_LEVEL": "DEBUG",
    }

    with patch.dict(os.environ, test_env, clear=True):
        # Force reload settings with new environment variables
        from core.config import load_settings
        import core.config

        core.config.settings = load_settings()

        # Create app - it will automatically detect testing environment and use temp DB paths
        app = create_app()

        # Manually initialize app state since lifespan might not run in tests
        from api.services.paper_service import PaperService
        from crawler.arxiv.client import ArxivClient
        from crawler.summarizer.openai_summarizer import OpenAISummarizer

        # Use tmp_path for testing databases
        db_path = tmp_path / "test.db"
        db_manager = SQLiteManager(db_path)
        db_manager.connect()
        db_manager.create_tables()

        llm_db_path = tmp_path / "test_llm.db"
        llm_db_manager = LLMSQLiteManager(llm_db_path)
        llm_db_manager.connect()
        llm_db_manager.create_tables()

        arxiv_client = ArxivClient(base_url=arxiv_url)
        summary_client = OpenAISummarizer(
            api_key="test-api-key",
            base_url=openai_url,
        )

        app.state.db_manager = db_manager
        app.state.llm_db_manager = llm_db_manager
        app.state.paper_service = PaperService()
        app.state.arxiv_client = arxiv_client
        app.state.summary_client = summary_client

        # Create default user for star functionality
        user_repository = UserRepository(db_manager)
        user = user_repository.get_user_by_id(DEFAULT_USER_ID)
        if user is None:
            from core.models import UserEntity

            user_entity = UserEntity(
                user_id=DEFAULT_USER_ID,
                email="test@example.com",
                display_name="test_user",
            )
            user_repository.create_user(user_entity)

        return TestClient(app)


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
