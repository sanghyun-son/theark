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
from core.extractors.concrete.arxiv_source_explorer import ArxivSourceExplorer
from core.extractors.concrete.historical_crawl_manager import HistoricalCrawlManager
from core.llm.openai_client import UnifiedOpenAIClient
from core.log import get_logger
from core.services.crawl_service import CrawlService
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

    # Setup ArXiv source explorer with mock server
    arxiv_explorer = ArxivSourceExplorer(
        api_base_url=mock_arxiv_extractor.base_url,
        delay_seconds=0.1,
        max_results_per_request=10,
    )
    app.state.arxiv_explorer = arxiv_explorer

    # Setup historical crawl manager
    historical_crawl_manager = HistoricalCrawlManager(
        categories=["cs.AI", "cs.LG"],
        rate_limit_delay=0.1,
        batch_size=10,
    )
    app.state.historical_crawl_manager = historical_crawl_manager

    # Setup CrawlService
    crawl_service = CrawlService(historical_crawl_manager)
    app.state.crawl_service = crawl_service

    yield TestClient(app)
