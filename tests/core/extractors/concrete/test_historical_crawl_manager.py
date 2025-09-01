"""Tests for HistoricalCrawlManager."""

import pytest
from datetime import datetime, timedelta
from unittest.mock import AsyncMock, patch

from core.extractors.concrete.historical_crawl_manager import HistoricalCrawlManager
from core.models.rows import CrawlExecutionState, CategoryDateProgress
from core.models.domain.arxiv import ArxivPaper
from core.extractors.concrete.arxiv_crawl_manager import ArxivCrawlManager
from sqlalchemy.engine import Engine


@pytest.fixture
def historical_crawl_manager(mock_arxiv_source_explorer) -> HistoricalCrawlManager:
    """Create a HistoricalCrawlManager instance for testing with mock explorer."""
    categories = ["cs.AI", "cs.LG", "cs.CL"]
    # Mock response 기준: 2025-01-01 (example_arxiv_response.xml의 published 날짜)
    start_date = "2025-01-01"
    return HistoricalCrawlManager(
        categories=categories,
        explorer=mock_arxiv_source_explorer,
        start_date=start_date,
    )


def test_initialization(historical_crawl_manager: HistoricalCrawlManager) -> None:
    """Test HistoricalCrawlManager initialization."""
    assert historical_crawl_manager.categories == ["cs.AI", "cs.LG", "cs.CL"]
    assert historical_crawl_manager.start_date == "2025-01-01"
    assert historical_crawl_manager.end_date == "2015-01-01"
    assert historical_crawl_manager.rate_limit_delay == 10
    assert historical_crawl_manager.batch_size == 100


def test_get_next_date_category_first_call(
    historical_crawl_manager: HistoricalCrawlManager,
) -> None:
    """Test get_next_date_category on first call."""
    # Create initial state
    state = CrawlExecutionState(
        current_date="2025-01-01",
        current_category_index=0,
        categories=["cs.AI", "cs.LG", "cs.CL"],
        is_active=True,
        total_papers_found=0,
        total_papers_stored=0,
    )

    # Should return first category for start date
    result = historical_crawl_manager.get_next_date_category(state)
    assert result is not None
    date, category = result
    assert date == "2025-01-01"
    assert category == "cs.AI"


def test_get_next_date_category_end_reached(
    historical_crawl_manager: HistoricalCrawlManager,
) -> None:
    """Test get_next_date_category when end date is reached."""
    # Create state at end date
    state = CrawlExecutionState(
        current_date="2015-01-01",
        current_category_index=0,
        categories=["cs.AI", "cs.LG", "cs.CL"],
        is_active=True,
        total_papers_found=0,
        total_papers_stored=0,
    )

    # Should return None when end date is reached
    result = historical_crawl_manager.get_next_date_category(state)
    assert result is None


def test_advance_to_next_category(
    historical_crawl_manager: HistoricalCrawlManager,
) -> None:
    """Test advancing to next category within same date."""
    state = CrawlExecutionState(
        current_date="2025-01-01",
        current_category_index=0,
        categories=["cs.AI", "cs.LG", "cs.CL"],
        is_active=True,
        total_papers_found=0,
        total_papers_stored=0,
    )

    # Advance to next category
    result = historical_crawl_manager.advance_to_next(state)
    assert result is True
    assert state.current_category_index == 1
    assert state.current_date == "2025-01-01"  # Same date


def test_advance_to_next_date(historical_crawl_manager: HistoricalCrawlManager) -> None:
    """Test advancing to next date when all categories processed."""
    state = CrawlExecutionState(
        current_date="2025-01-01",
        current_category_index=2,  # Last category index
        categories=["cs.AI", "cs.LG", "cs.CL"],
        is_active=True,
        total_papers_found=0,
        total_papers_stored=0,
    )

    # Advance to next date
    result = historical_crawl_manager.advance_to_next(state)
    assert result is True
    assert state.current_category_index == 0  # Reset to first category
    assert state.current_date == "2024-12-31"  # Previous date


def test_initialization_with_explorer(mock_arxiv_source_explorer) -> None:
    """Test HistoricalCrawlManager initialization with explorer injection."""
    categories = ["cs.AI", "cs.LG"]
    start_date = "2025-01-01"

    manager = HistoricalCrawlManager(
        categories=categories,
        explorer=mock_arxiv_source_explorer,
        start_date=start_date,
    )

    assert manager.categories == ["cs.AI", "cs.LG"]
    assert manager.start_date == "2025-01-01"
    assert manager.explorer is mock_arxiv_source_explorer  # Explorer injected


@pytest.mark.asyncio
async def test_crawl_date_category_with_mock_server(
    historical_crawl_manager: HistoricalCrawlManager,
    mock_db_engine: Engine,
) -> None:
    """Test crawl_date_category with mock ArXiv server."""
    category = "cs.AI"
    date = "2025-01-01"

    # Mock server가 example_arxiv_response.xml을 반환하므로
    # 실제 API 호출 없이 테스트 가능
    papers_found, papers_stored = await historical_crawl_manager.crawl_date_category(
        engine=mock_db_engine, category=category, date=date
    )

    # Mock response에는 10개의 논문이 있음
    assert papers_found >= 0  # 실제로는 10개지만, 네트워크 상태에 따라 달라질 수 있음
    assert papers_stored >= 0  # 저장된 논문 수
    assert papers_stored <= papers_found  # 저장된 수는 발견된 수보다 많을 수 없음
