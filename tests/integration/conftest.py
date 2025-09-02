"""Common fixtures for integration tests."""

import os
from collections.abc import AsyncGenerator
from pathlib import Path

import pytest_asyncio
from fastapi.testclient import TestClient
from sqlalchemy.engine import Engine

from api.app import create_app
from api.services.app_initializer import AppServiceInitializer
from core.config import load_settings
from core.log import get_logger

logger = get_logger(__name__)


@pytest_asyncio.fixture
async def integration_client(
    tmp_path: Path,
    mock_db_engine: Engine,
    mock_arxiv_server,
    mock_openai_server,
) -> AsyncGenerator[TestClient, None]:
    """Create a test client using AppServiceInitializer with mock dependencies."""

    # Set environment to testing for integration tests
    os.environ["THEARK_ENV"] = "testing"

    app = create_app()
    settings = load_settings()
    app.state.settings = settings

    # Use AppServiceInitializer with mock dependencies
    initializer = AppServiceInitializer(settings)

    # Initialize all services with mock dependencies
    await initializer.initialize_all_services(
        app=app,
        engine=mock_db_engine,
        arxiv_base_url=f"http://{mock_arxiv_server.host}:{mock_arxiv_server.port}/api/query",
        llm_base_url=f"http://{mock_openai_server.host}:{mock_openai_server.port}/v1",
        llm_api_key="test-api-key",
    )

    yield TestClient(app)
