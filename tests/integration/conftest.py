"""Common fixtures for integration tests."""

import os
from collections.abc import AsyncGenerator
from pathlib import Path

import pytest_asyncio
from fastapi.testclient import TestClient
from sqlalchemy.engine import Engine

from api.app import create_app
from core.batch.background_manager import BackgroundBatchManager
from core.config import load_settings
from core.database.engine import create_database_tables
from core.extractors import extractor_factory
from core.llm.openai_client import UnifiedOpenAIClient
from core.log import get_logger
from core.services.summarization_service import PaperSummarizationService

logger = get_logger(__name__)


@pytest_asyncio.fixture
async def integration_client(
    tmp_path: Path,
    mock_db_engine: Engine,
    mock_arxiv_extractor,
    mock_openai_client: UnifiedOpenAIClient,
) -> AsyncGenerator[TestClient, None]:
    """Create a test client with real database managers using mock servers."""

    # Set environment to testing for integration tests
    os.environ["THEARK_ENV"] = "testing"

    app = create_app()
    app.state.settings = load_settings()

    # Set up app state with our test engine and create tables
    app.state.engine = mock_db_engine
    create_database_tables(mock_db_engine)
    app.state.summary_client = mock_openai_client
    app.state.background_batch_manager = BackgroundBatchManager(
        PaperSummarizationService(version="test"),
        batch_enabled=True,
    )

    extractor_factory.register_extractor(
        "arxiv",
        mock_arxiv_extractor,
    )

    yield TestClient(app)
