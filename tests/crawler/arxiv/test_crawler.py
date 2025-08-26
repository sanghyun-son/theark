"""Tests for ArxivCrawler."""

import asyncio
from datetime import datetime
from unittest.mock import AsyncMock, MagicMock

import pytest

from crawler.arxiv.crawler import (
    ArxivCrawler,
    CrawlConfig,
    CrawlStatus,
)
from crawler.arxiv.exceptions import ArxivNotFoundError
from core.models.database.entities import PaperEntity as Paper


def test_crawl_status_values():
    """Test that all status values are defined."""
    assert CrawlStatus.IDLE.value == "idle"
    assert CrawlStatus.RUNNING.value == "running"
    assert CrawlStatus.PAUSED.value == "paused"
    assert CrawlStatus.STOPPED.value == "stopped"
    assert CrawlStatus.ERROR.value == "error"


def test_crawl_config_default():
    """Test default configuration values."""
    config = CrawlConfig()

    # Test that default configs are created
    assert config.on_demand is not None
    assert config.periodic is not None


def test_crawl_config_custom():
    """Test custom configuration values."""
    from crawler.arxiv.on_demand_crawler import OnDemandCrawlConfig
    from crawler.arxiv.periodic_crawler import PeriodicCrawlConfig

    config = CrawlConfig(
        periodic=PeriodicCrawlConfig(background_interval=1800),
        on_demand=OnDemandCrawlConfig(recent_papers_limit=100),
    )

    assert config.periodic.background_interval == 1800
    assert config.on_demand.recent_papers_limit == 100


@pytest.fixture
def arxiv_crawler(mock_db_manager):
    """Create an ArxivCrawler instance for testing."""
    from crawler.arxiv.on_demand_crawler import OnDemandCrawlConfig
    from crawler.arxiv.periodic_crawler import PeriodicCrawlConfig

    config = CrawlConfig(
        periodic=PeriodicCrawlConfig(
            background_interval=1
        ),  # Short interval for testing
        on_demand=OnDemandCrawlConfig(),
    )
    return ArxivCrawler(mock_db_manager, config=config)


def test_arxiv_crawler_initialization(arxiv_crawler):
    """Test crawler initialization."""
    assert arxiv_crawler.db_manager is not None
    assert arxiv_crawler.config is not None
    assert arxiv_crawler.status == CrawlStatus.IDLE
    assert arxiv_crawler.on_demand_crawler is not None
    assert arxiv_crawler.periodic_crawler is not None


def test_arxiv_crawler_initialization_with_callbacks(mock_db_manager):
    """Test crawler initialization with callbacks."""
    callback_called = False
    error_called = False

    async def on_paper_crawled(paper):
        nonlocal callback_called
        callback_called = True

    async def on_error(exception):
        nonlocal error_called
        error_called = True

    crawler = ArxivCrawler(
        mock_db_manager,
        on_paper_crawled=on_paper_crawled,
        on_error=on_error,
    )

    assert crawler.on_paper_crawled == on_paper_crawled
    assert crawler.on_error == on_error


@pytest.mark.asyncio
async def test_arxiv_crawler_context_manager(arxiv_crawler):
    """Test crawler as async context manager."""
    async with arxiv_crawler as crawler:
        assert crawler.status == CrawlStatus.IDLE
        # Context manager should start the crawler
        assert crawler.on_demand_crawler.core.stats.start_time is not None

    # Context manager should stop the crawler
    assert crawler.status == CrawlStatus.STOPPED


@pytest.mark.asyncio
async def test_arxiv_crawler_start_and_stop(arxiv_crawler):
    """Test crawler start and stop."""
    await arxiv_crawler.start()
    assert arxiv_crawler.status == CrawlStatus.IDLE

    await arxiv_crawler.stop()
    assert arxiv_crawler.status == CrawlStatus.STOPPED


@pytest.mark.asyncio
async def test_arxiv_crawler_start_background_loop(arxiv_crawler):
    """Test starting background crawling loop."""
    await arxiv_crawler.start()
    await arxiv_crawler.start_background_loop()

    assert arxiv_crawler.status == CrawlStatus.RUNNING

    # Check that background task is running
    status = await arxiv_crawler.get_status()
    assert status.background_task_running is True

    await arxiv_crawler.stop()


@pytest.mark.asyncio
async def test_arxiv_crawler_stop_background_loop(arxiv_crawler):
    """Test stopping background crawling loop."""
    await arxiv_crawler.start()
    await arxiv_crawler.start_background_loop()

    await arxiv_crawler.stop_background_loop()

    assert arxiv_crawler.status == CrawlStatus.PAUSED

    # Check that background task is no longer running
    status = await arxiv_crawler.get_status()
    assert status.background_task_running is False

    await arxiv_crawler.stop()


@pytest.mark.asyncio
async def test_arxiv_crawler_crawl_single_paper_success(
    arxiv_crawler, mock_arxiv_client
):
    """Test successful single paper crawling."""
    # Setup mock paper
    mock_paper = Paper(
        arxiv_id="1706.03762",
        title="Test Paper",
        abstract="Test abstract",
        primary_category="cs.AI",
        categories="cs.AI",
        authors="Test Author",
        url_abs="http://arxiv.org/abs/1706.03762",
        url_pdf="http://arxiv.org/pdf/1706.03762",
        published_at="2023-08-02T00:41:18Z",
        updated_at="2023-08-02T00:41:18Z",
    )

    # Mock the core crawler's crawl_single_paper method
    async def mock_crawl_single_paper(identifier, db_manager, arxiv_client):
        return mock_paper

    arxiv_crawler.on_demand_crawler.core.crawl_single_paper = mock_crawl_single_paper

    await arxiv_crawler.start()

    # Test crawling
    result = await arxiv_crawler.crawl_single_paper(
        "1706.03762", arxiv_crawler.db_manager, mock_arxiv_client
    )

    assert result is not None
    assert result.arxiv_id == "1706.03762"

    await arxiv_crawler.stop()


@pytest.mark.asyncio
async def test_arxiv_crawler_crawl_single_paper_not_found(
    arxiv_crawler, mock_arxiv_client
):
    """Test crawling non-existent paper."""

    # Mock the core crawler's crawl_single_paper method to return None
    async def mock_crawl_single_paper(identifier, db_manager, arxiv_client):
        return None

    arxiv_crawler.on_demand_crawler.core.crawl_single_paper = mock_crawl_single_paper

    await arxiv_crawler.start()

    # Test crawling
    result = await arxiv_crawler.crawl_single_paper(
        "9999.99999", arxiv_crawler.db_manager, mock_arxiv_client
    )

    assert result is None

    await arxiv_crawler.stop()


@pytest.mark.asyncio
async def test_arxiv_crawler_crawl_single_paper_already_exists(
    arxiv_crawler, mock_arxiv_client
):
    """Test crawling paper that already exists."""
    existing_paper = Paper(
        arxiv_id="1706.03762",
        title="Existing Paper",
        abstract="Existing abstract",
        primary_category="cs.AI",
        categories="cs.AI",
        authors="Existing Author",
        url_abs="http://arxiv.org/abs/1706.03762",
        url_pdf="http://arxiv.org/pdf/1706.03762",
        published_at="2023-08-02T00:41:18Z",
        updated_at="2023-08-02T00:41:18Z",
    )

    # Mock the core crawler's crawl_single_paper method to return existing paper
    async def mock_crawl_single_paper(identifier, db_manager, arxiv_client):
        return existing_paper

    arxiv_crawler.on_demand_crawler.core.crawl_single_paper = mock_crawl_single_paper

    await arxiv_crawler.start()

    # Test crawling
    result = await arxiv_crawler.crawl_single_paper(
        "1706.03762", arxiv_crawler.db_manager, mock_arxiv_client
    )

    assert result == existing_paper

    await arxiv_crawler.stop()


@pytest.mark.asyncio
async def test_arxiv_crawler_crawl_recent_papers_placeholder(
    arxiv_crawler, mock_arxiv_client
):
    """Test recent papers crawling (placeholder)."""
    await arxiv_crawler.start()

    result = await arxiv_crawler.crawl_recent_papers(mock_arxiv_client, limit=10)

    assert result == []  # Placeholder returns empty list

    await arxiv_crawler.stop()


@pytest.mark.asyncio
async def test_arxiv_crawler_crawl_monthly_papers_placeholder(arxiv_crawler):
    """Test monthly papers crawling (placeholder)."""
    await arxiv_crawler.start()

    result = await arxiv_crawler.crawl_monthly_papers(2024, 1, limit=10)

    assert result == []  # Placeholder returns empty list

    await arxiv_crawler.stop()


@pytest.mark.asyncio
async def test_arxiv_crawler_get_status(arxiv_crawler):
    """Test status retrieval."""
    await arxiv_crawler.start()

    status = await arxiv_crawler.get_status()

    assert hasattr(status, "status")
    assert hasattr(status, "background_task_running")
    assert hasattr(status, "on_demand")
    assert hasattr(status, "periodic")
    assert status.status == "idle"
    assert status.background_task_running is False

    await arxiv_crawler.stop()


@pytest.mark.asyncio
async def test_arxiv_crawler_get_status_with_background_loop(arxiv_crawler):
    """Test status retrieval with background loop running."""
    await arxiv_crawler.start()
    await arxiv_crawler.start_background_loop()

    status = await arxiv_crawler.get_status()

    assert status.status == "running"
    assert status.background_task_running is True

    await arxiv_crawler.stop_background_loop()
    await arxiv_crawler.stop()


@pytest.mark.asyncio
async def test_arxiv_crawler_callback_on_paper_crawled(
    mock_db_manager, mock_arxiv_client
):
    """Test callback when paper is crawled."""
    # Use a simple callback tracker
    callback_tracker = {"called": False, "paper": None}

    async def on_paper_crawled(paper):
        callback_tracker["called"] = True
        callback_tracker["paper"] = paper

    crawler = ArxivCrawler(mock_db_manager, on_paper_crawled=on_paper_crawled)

    # Setup mock paper
    mock_paper = Paper(
        arxiv_id="1706.03762",
        title="Test Paper",
        abstract="Test abstract",
        primary_category="cs.AI",
        categories="cs.AI",
        authors="Test Author",
        url_abs="http://arxiv.org/abs/1706.03762",
        url_pdf="http://arxiv.org/pdf/1706.03762",
        published_at="2023-08-02T00:41:18Z",
        updated_at="2023-08-02T00:41:18Z",
    )

    # Mock the on_demand_crawler's crawl_single_paper method to trigger callback
    async def mock_crawl_single_paper_with_callback(
        identifier, db_manager, arxiv_client
    ):
        # Trigger the callback through the core's callback chain
        if crawler.on_demand_crawler.core.on_paper_crawled:
            await crawler.on_demand_crawler.core.on_paper_crawled(mock_paper)
        return mock_paper

    crawler.on_demand_crawler.crawl_single_paper = mock_crawl_single_paper_with_callback

    await crawler.start()
    await crawler.crawl_single_paper("1706.03762", mock_db_manager, mock_arxiv_client)

    # Verify callback was called
    assert callback_tracker["called"] is True
    assert callback_tracker["paper"] == mock_paper

    await crawler.stop()


@pytest.mark.asyncio
async def test_arxiv_crawler_callback_on_error(mock_db_manager, mock_arxiv_client):
    """Test callback when error occurs."""
    # Use a simple callback tracker
    error_tracker = {"called": False, "exception": None}

    async def on_error(exception):
        error_tracker["called"] = True
        error_tracker["exception"] = exception

    crawler = ArxivCrawler(mock_db_manager, on_error=on_error)

    # Mock the on_demand_crawler's crawl_single_paper method to trigger error callback
    async def mock_crawl_single_paper_with_error(identifier, db_manager, arxiv_client):
        error = Exception("Test error")
        # Trigger the error callback through the core's callback chain
        if crawler.on_demand_crawler.core.on_error:
            await crawler.on_demand_crawler.core.on_error(error)
        return None

    crawler.on_demand_crawler.crawl_single_paper = mock_crawl_single_paper_with_error

    await crawler.start()
    await crawler.crawl_single_paper("1706.03762", mock_db_manager, mock_arxiv_client)

    # Verify error callback was called
    assert error_tracker["called"] is True
    assert error_tracker["exception"] is not None
    assert str(error_tracker["exception"]) == "Test error"

    await crawler.stop()


@pytest.mark.asyncio
async def test_arxiv_crawler_background_loop_stop_signal(arxiv_crawler):
    """Test that background loop stops when signaled."""
    await arxiv_crawler.start()
    await arxiv_crawler.start_background_loop()

    # Wait a bit for loop to start
    await asyncio.sleep(0.1)

    # Stop the loop
    await arxiv_crawler.stop_background_loop()

    # Verify loop stopped
    assert arxiv_crawler.status == CrawlStatus.PAUSED

    # Check that task is no longer running
    status = await arxiv_crawler.get_status()
    assert status.background_task_running is False

    await arxiv_crawler.stop()


@pytest.mark.asyncio
async def test_arxiv_crawler_multiple_start_stop_calls(arxiv_crawler):
    """Test multiple start/stop calls are handled gracefully."""
    await arxiv_crawler.start()
    await arxiv_crawler.start()  # Should be ignored

    await arxiv_crawler.stop()
    await arxiv_crawler.stop()  # Should be ignored

    assert arxiv_crawler.status == CrawlStatus.STOPPED
