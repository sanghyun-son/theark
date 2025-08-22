"""Tests for ArxivCrawler."""

import pytest
import asyncio
from datetime import datetime
from unittest.mock import AsyncMock, MagicMock

from crawler.arxiv.crawler import (
    ArxivCrawler,
    CrawlStatus,
    CrawlStrategy,
    CrawlConfig,
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


class TestCrawlStrategy:
    """Test CrawlStrategy enum."""

    def test_strategy_values(self):
        """Test that all strategy values are defined."""
        assert CrawlStrategy.SINGLE_PAPER.value == "single_paper"
        assert CrawlStrategy.RECENT_PAPERS.value == "recent_papers"
        assert CrawlStrategy.MONTHLY_PAPERS.value == "monthly_papers"
        assert CrawlStrategy.YEARLY_PAPERS.value == "yearly_papers"


class TestCrawlConfig:
    """Test CrawlConfig dataclass."""

    def test_default_config(self):
        """Test default configuration values."""
        from crawler.arxiv.constants import (
            DEFAULT_BACKGROUND_INTERVAL,
            DEFAULT_MAX_CONCURRENT_PAPERS,
            DEFAULT_RATE_LIMIT,
            DEFAULT_MAX_PAPERS_PER_BATCH,
            DEFAULT_MAX_RETRIES,
            DEFAULT_RETRY_DELAY,
            DEFAULT_BATCH_SIZE,
            DEFAULT_RECENT_PAPERS_LIMIT,
            DEFAULT_MONTHLY_PAPERS_LIMIT,
        )
        
        config = CrawlConfig()

        assert config.background_interval == DEFAULT_BACKGROUND_INTERVAL
        assert config.max_concurrent_papers == DEFAULT_MAX_CONCURRENT_PAPERS
        assert config.requests_per_second == DEFAULT_RATE_LIMIT
        assert config.max_papers_per_batch == DEFAULT_MAX_PAPERS_PER_BATCH
        assert config.max_retries == DEFAULT_MAX_RETRIES
        assert config.retry_delay == DEFAULT_RETRY_DELAY
        assert config.batch_size == DEFAULT_BATCH_SIZE
        assert config.recent_papers_limit == DEFAULT_RECENT_PAPERS_LIMIT
        assert config.monthly_papers_limit == DEFAULT_MONTHLY_PAPERS_LIMIT

    def test_custom_config(self):
        """Test custom configuration values."""
        config = CrawlConfig(
            background_interval=1800,
            max_concurrent_papers=5,
            requests_per_second=2.0,
        )

        assert config.background_interval == 1800
        assert config.max_concurrent_papers == 5
        assert config.requests_per_second == 2.0


class TestArxivCrawler:
    """Test ArxivCrawler functionality."""

    @pytest.fixture
    def mock_db_manager(self):
        """Create a mock database manager."""
        manager = AsyncMock()
        manager.__aenter__ = AsyncMock(return_value=manager)
        manager.__aexit__ = AsyncMock(return_value=None)
        return manager

    @pytest.fixture
    def mock_paper_repo(self):
        """Create a mock paper repository."""
        repo = AsyncMock()
        repo.get_by_arxiv_id = AsyncMock(return_value=None)
        repo.create = AsyncMock()
        return repo

    @pytest.fixture
    def mock_event_repo(self):
        """Create a mock event repository."""
        repo = AsyncMock()
        repo.create = AsyncMock()
        return repo

    @pytest.fixture
    def crawler(self, mock_db_manager):
        """Create a crawler instance for testing."""
        config = CrawlConfig(
            background_interval=1
        )  # Short interval for testing
        return ArxivCrawler(mock_db_manager, config=config)

    def test_initialization(self, mock_db_manager):
        """Test crawler initialization."""
        config = CrawlConfig()
        crawler = ArxivCrawler(mock_db_manager, config=config)

        assert crawler.db_manager == mock_db_manager
        assert crawler.config == config
        assert crawler.status == CrawlStatus.IDLE
        assert crawler._background_task is None
        assert crawler.stats["papers_crawled"] == 0
        assert crawler.stats["papers_failed"] == 0

    def test_initialization_with_callbacks(self, mock_db_manager):
        """Test crawler initialization with callbacks."""
        on_paper_crawled = AsyncMock()
        on_error = AsyncMock()

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
        assert crawler.stats["start_time"] is not None

        # Stop crawler
        await crawler.stop()
        assert crawler.status == CrawlStatus.STOPPED

    @pytest.mark.asyncio
    async def test_start_background_loop(self, crawler):
        """Test starting background loop."""
        await crawler.start()
        await crawler.start_background_loop()

        assert crawler.status == CrawlStatus.RUNNING
        assert crawler._background_task is not None
        assert not crawler._background_task.done()

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
        assert (
            crawler._background_task is None or crawler._background_task.done()
        )

        await crawler.stop()

    @pytest.mark.asyncio
    async def test_crawl_single_paper_success(self, crawler, mock_paper_repo):
        """Test successful single paper crawling."""
        # Setup mocks
        crawler.paper_repo = mock_paper_repo
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
        mock_paper_repo.create.return_value = mock_paper
        # Ensure the mock is properly configured for async calls
        mock_paper_repo.get_by_arxiv_id = AsyncMock(return_value=None)
        mock_paper_repo.create = AsyncMock(return_value=mock_paper)

        # Mock the _crawl_paper method to avoid real API calls
        async def mock_crawl_paper(identifier):
            return mock_paper

        crawler._crawl_paper = mock_crawl_paper

        await crawler.start()

        # Test crawling
        result = await crawler.crawl_single_paper("1706.03762")

        assert result is not None
        assert result.arxiv_id == "1706.03762"
        assert crawler.stats["papers_crawled"] == 1
        assert crawler.stats["papers_failed"] == 0

        await crawler.stop()

    @pytest.mark.asyncio
    async def test_crawl_single_paper_not_found(self, crawler, mock_paper_repo):
        """Test crawling non-existent paper."""
        # Setup mocks to simulate paper not found
        crawler.paper_repo = mock_paper_repo
        mock_paper_repo.get_by_arxiv_id = AsyncMock(
            side_effect=ArxivNotFoundError("Paper not found")
        )

        # Mock the _crawl_paper method to return None (not found)
        async def mock_crawl_paper(identifier):
            return None

        crawler._crawl_paper = mock_crawl_paper

        await crawler.start()

        # Test crawling
        result = await crawler.crawl_single_paper("9999.99999")

        assert result is None
        assert crawler.stats["papers_crawled"] == 0
        assert crawler.stats["papers_failed"] == 1

        await crawler.stop()

    @pytest.mark.asyncio
    async def test_crawl_single_paper_already_exists(
        self, crawler, mock_paper_repo
    ):
        """Test crawling paper that already exists."""
        # Setup mocks
        crawler.paper_repo = mock_paper_repo
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
        mock_paper_repo.get_by_arxiv_id.return_value = existing_paper
        # Ensure the mock is properly configured for async calls
        mock_paper_repo.get_by_arxiv_id = AsyncMock(return_value=existing_paper)

        # Mock the _crawl_paper method to return existing paper
        async def mock_crawl_paper(identifier):
            return existing_paper

        crawler._crawl_paper = mock_crawl_paper

        await crawler.start()

        # Test crawling
        result = await crawler.crawl_single_paper("1706.03762")

        assert result == existing_paper
        assert crawler.stats["papers_crawled"] == 1
        assert crawler.stats["papers_failed"] == 0

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

        assert "status" in status
        assert "background_task_running" in status
        assert "stats" in status
        assert "config" in status
        assert status["status"] == "idle"
        assert status["background_task_running"] is False

        await crawler.stop()

    @pytest.mark.asyncio
    async def test_get_status_with_background_loop(self, crawler):
        """Test status retrieval with background loop running."""
        await crawler.start()
        await crawler.start_background_loop()

        status = await crawler.get_status()

        assert status["status"] == "running"
        assert status["background_task_running"] is True

        await crawler.stop_background_loop()
        await crawler.stop()

    @pytest.mark.asyncio
    async def test_callback_on_paper_crawled(self, mock_db_manager):
        """Test callback when paper is crawled."""
        on_paper_crawled = AsyncMock()
        crawler = ArxivCrawler(
            mock_db_manager, on_paper_crawled=on_paper_crawled
        )

        # Setup mocks
        mock_paper_repo = AsyncMock()
        mock_paper_repo.get_by_arxiv_id.return_value = None
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
        mock_paper_repo.create.return_value = mock_paper
        # Ensure the mock is properly configured for async calls
        mock_paper_repo.get_by_arxiv_id = AsyncMock(return_value=None)
        mock_paper_repo.create = AsyncMock(return_value=mock_paper)
        crawler.paper_repo = mock_paper_repo

        # Mock the _crawl_paper method to return the mock paper
        async def mock_crawl_paper(identifier):
            return mock_paper

        crawler._crawl_paper = mock_crawl_paper

        await crawler.start()
        await crawler.crawl_single_paper("1706.03762")

        # Verify callback was called
        on_paper_crawled.assert_called_once_with(mock_paper)

        await crawler.stop()

    @pytest.mark.asyncio
    async def test_callback_on_error(self, mock_db_manager):
        """Test callback when error occurs."""
        on_error = AsyncMock()
        crawler = ArxivCrawler(mock_db_manager, on_error=on_error)

        # Setup mocks to simulate error
        mock_paper_repo = AsyncMock()
        mock_paper_repo.get_by_arxiv_id.side_effect = Exception("Test error")
        crawler.paper_repo = mock_paper_repo

        await crawler.start()
        await crawler.crawl_single_paper("1706.03762")

        # Verify error callback was called
        on_error.assert_called_once()

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
        assert crawler._background_task.done()

        await crawler.stop()

    @pytest.mark.asyncio
    async def test_multiple_start_stop_calls(self, crawler):
        """Test multiple start/stop calls are handled gracefully."""
        await crawler.start()
        await crawler.start()  # Should be ignored

        await crawler.stop()
        await crawler.stop()  # Should be ignored

        assert crawler.status == CrawlStatus.STOPPED
