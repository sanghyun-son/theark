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
from crawler.database import Paper


class TestCrawlStatus:
    """Test CrawlStatus enum."""

    def test_status_values(self):
        """Test that all status values are defined."""
        assert CrawlStatus.IDLE.value == "idle"
        assert CrawlStatus.RUNNING.value == "running"
        assert CrawlStatus.PAUSED.value == "paused"
        assert CrawlStatus.STOPPED.value == "stopped"
        assert CrawlStatus.ERROR.value == "error"


# CrawlStrategy has been removed - these tests are no longer needed


class TestCrawlConfig:
    """Test CrawlConfig dataclass."""

    def test_default_config(self):
        """Test default configuration values."""
        config = CrawlConfig()

        # Test that default configs are created
        assert config.on_demand is not None
        assert config.periodic is not None

    def test_custom_config(self):
        """Test custom configuration values."""
        from crawler.arxiv.on_demand_crawler import OnDemandCrawlConfig
        from crawler.arxiv.periodic_crawler import PeriodicCrawlConfig

        config = CrawlConfig(
            periodic=PeriodicCrawlConfig(background_interval=1800),
            on_demand=OnDemandCrawlConfig(recent_papers_limit=100),
        )

        assert config.periodic.background_interval == 1800
        assert config.on_demand.recent_papers_limit == 100


class TestArxivCrawler:
    """Test ArxivCrawler functionality."""

    @pytest.fixture
    def mock_db_manager(self):
        """Create a mock database manager."""
        manager = MagicMock()
        manager.__enter__ = MagicMock(return_value=manager)
        manager.__exit__ = MagicMock(return_value=None)
        return manager

    @pytest.fixture
    def mock_paper_repo(self):
        """Create a mock paper repository."""
        repo = MagicMock()
        repo.get_by_arxiv_id = MagicMock(return_value=None)
        repo.create = MagicMock()
        return repo

    @pytest.fixture
    def mock_event_repo(self):
        """Create a mock event repository."""
        repo = MagicMock()
        repo.create = MagicMock()
        return repo

    @pytest.fixture
    def crawler(self, mock_db_manager):
        """Create a crawler instance for testing."""
        from crawler.arxiv.on_demand_crawler import OnDemandCrawlConfig
        from crawler.arxiv.periodic_crawler import PeriodicCrawlConfig

        config = CrawlConfig(
            periodic=PeriodicCrawlConfig(
                background_interval=1
            ),  # Short interval for testing
            on_demand=OnDemandCrawlConfig(),
        )
        return ArxivCrawler(mock_db_manager, config=config)

    def test_initialization(self, mock_db_manager):
        """Test crawler initialization."""
        config = CrawlConfig()
        crawler = ArxivCrawler(mock_db_manager, config=config)

        assert crawler.db_manager == mock_db_manager
        assert crawler.config == config
        assert crawler.status == CrawlStatus.IDLE
        assert crawler.on_demand_crawler is not None
        assert crawler.periodic_crawler is not None

    def test_initialization_with_callbacks(self, mock_db_manager):
        """Test crawler initialization with callbacks."""

        # Create simple async functions instead of AsyncMock
        async def on_paper_crawled(paper):
            pass

        async def on_error(exception):
            pass

        crawler = ArxivCrawler(
            mock_db_manager,
            on_paper_crawled=on_paper_crawled,
            on_error=on_error,
        )

        assert crawler.on_paper_crawled == on_paper_crawled
        assert crawler.on_error == on_error

    @pytest.mark.asyncio
    async def test_context_manager(self, mock_db_manager):
        """Test async context manager functionality."""
        async with ArxivCrawler(mock_db_manager) as crawler:
            assert crawler.status == CrawlStatus.IDLE

    @pytest.mark.asyncio
    async def test_start_and_stop(self, crawler):
        """Test start and stop functionality."""
        # Start crawler
        await crawler.start()
        assert crawler.status == CrawlStatus.IDLE

        # Stop crawler
        await crawler.stop()
        assert crawler.status == CrawlStatus.STOPPED

    @pytest.mark.asyncio
    async def test_start_background_loop(self, crawler):
        """Test starting background loop."""
        await crawler.start()
        await crawler.start_background_loop()

        assert crawler.status == CrawlStatus.RUNNING

        # Check task manager status
        status = await crawler.get_status()
        assert status.background_task_running is True

        # Clean up
        await crawler.stop_background_loop()
        await crawler.stop()

    @pytest.mark.asyncio
    async def test_stop_background_loop(self, crawler):
        """Test stopping background loop."""
        await crawler.start()
        await crawler.start_background_loop()
        await crawler.stop_background_loop()

        assert crawler.status == CrawlStatus.PAUSED

        # Check that background task is no longer running
        status = await crawler.get_status()
        assert status.background_task_running is False

        await crawler.stop()

    @pytest.mark.asyncio
    async def test_crawl_single_paper_success(self, crawler, mock_paper_repo):
        """Test successful single paper crawling."""
        # Setup mocks
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
        async def mock_crawl_single_paper(identifier):
            return mock_paper

        crawler.on_demand_crawler.core.crawl_single_paper = mock_crawl_single_paper

        await crawler.start()

        # Test crawling
        result = await crawler.crawl_single_paper("1706.03762")

        assert result is not None
        assert result.arxiv_id == "1706.03762"

        await crawler.stop()

    @pytest.mark.asyncio
    async def test_crawl_single_paper_not_found(self, crawler, mock_paper_repo):
        """Test crawling non-existent paper."""

        # Mock the core crawler's crawl_single_paper method to return None
        async def mock_crawl_single_paper(identifier):
            return None

        crawler.on_demand_crawler.core.crawl_single_paper = mock_crawl_single_paper

        await crawler.start()

        # Test crawling
        result = await crawler.crawl_single_paper("9999.99999")

        assert result is None

        await crawler.stop()

    @pytest.mark.asyncio
    async def test_crawl_single_paper_already_exists(self, crawler, mock_paper_repo):
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
        async def mock_crawl_single_paper(identifier):
            return existing_paper

        crawler.on_demand_crawler.core.crawl_single_paper = mock_crawl_single_paper

        await crawler.start()

        # Test crawling
        result = await crawler.crawl_single_paper("1706.03762")

        assert result == existing_paper

        await crawler.stop()

    @pytest.mark.asyncio
    async def test_crawl_recent_papers_placeholder(self, crawler):
        """Test recent papers crawling (placeholder)."""
        await crawler.start()

        result = await crawler.crawl_recent_papers(limit=10)

        assert result == []  # Placeholder returns empty list

        await crawler.stop()

    @pytest.mark.asyncio
    async def test_crawl_monthly_papers_placeholder(self, crawler):
        """Test monthly papers crawling (placeholder)."""
        await crawler.start()

        result = await crawler.crawl_monthly_papers(2024, 1, limit=10)

        assert result == []  # Placeholder returns empty list

        await crawler.stop()

    @pytest.mark.asyncio
    async def test_get_status(self, crawler):
        """Test status retrieval."""
        await crawler.start()

        status = await crawler.get_status()

        assert hasattr(status, "status")
        assert hasattr(status, "background_task_running")
        assert hasattr(status, "on_demand")
        assert hasattr(status, "periodic")
        assert status.status == "idle"
        assert status.background_task_running is False

        await crawler.stop()

    @pytest.mark.asyncio
    async def test_get_status_with_background_loop(self, crawler):
        """Test status retrieval with background loop running."""
        await crawler.start()
        await crawler.start_background_loop()

        status = await crawler.get_status()

        assert status.status == "running"
        assert status.background_task_running is True

        await crawler.stop_background_loop()
        await crawler.stop()

    @pytest.mark.asyncio
    async def test_callback_on_paper_crawled(self, mock_db_manager):
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
        async def mock_crawl_single_paper_with_callback(identifier):
            # Trigger the callback through the core's callback chain
            if crawler.on_demand_crawler.core.on_paper_crawled:
                await crawler.on_demand_crawler.core.on_paper_crawled(mock_paper)
            return mock_paper

        crawler.on_demand_crawler.crawl_single_paper = (
            mock_crawl_single_paper_with_callback
        )

        await crawler.start()
        await crawler.crawl_single_paper("1706.03762")

        # Verify callback was called
        assert callback_tracker["called"] is True
        assert callback_tracker["paper"] == mock_paper

        await crawler.stop()

    @pytest.mark.asyncio
    async def test_callback_on_error(self, mock_db_manager):
        """Test callback when error occurs."""
        # Use a simple callback tracker
        error_tracker = {"called": False, "exception": None}

        async def on_error(exception):
            error_tracker["called"] = True
            error_tracker["exception"] = exception

        crawler = ArxivCrawler(mock_db_manager, on_error=on_error)

        # Mock the on_demand_crawler's crawl_single_paper method to trigger error callback
        async def mock_crawl_single_paper_with_error(identifier):
            error = Exception("Test error")
            # Trigger the error callback through the core's callback chain
            if crawler.on_demand_crawler.core.on_error:
                await crawler.on_demand_crawler.core.on_error(error)
            return None

        crawler.on_demand_crawler.crawl_single_paper = (
            mock_crawl_single_paper_with_error
        )

        await crawler.start()
        await crawler.crawl_single_paper("1706.03762")

        # Verify error callback was called
        assert error_tracker["called"] is True
        assert error_tracker["exception"] is not None
        assert str(error_tracker["exception"]) == "Test error"

        await crawler.stop()

    @pytest.mark.asyncio
    async def test_background_loop_stop_signal(self, crawler):
        """Test that background loop stops when signaled."""
        await crawler.start()
        await crawler.start_background_loop()

        # Wait a bit for loop to start
        await asyncio.sleep(0.1)

        # Stop the loop
        await crawler.stop_background_loop()

        # Verify loop stopped
        assert crawler.status == CrawlStatus.PAUSED

        # Check that task is no longer running
        status = await crawler.get_status()
        assert status.background_task_running is False

        await crawler.stop()

    @pytest.mark.asyncio
    async def test_multiple_start_stop_calls(self, crawler):
        """Test multiple start/stop calls are handled gracefully."""
        await crawler.start()
        await crawler.start()  # Should be ignored

        await crawler.stop()
        await crawler.stop()  # Should be ignored

        assert crawler.status == CrawlStatus.STOPPED
