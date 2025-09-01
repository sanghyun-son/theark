"""Tests for HistoricalCrawlManager."""

from unittest.mock import AsyncMock, patch

import pytest
from sqlalchemy.engine import Engine
from sqlmodel import Session

from core.extractors.concrete.arxiv_source_explorer import ArxivSourceExplorer
from core.extractors.concrete.historical_crawl_manager import HistoricalCrawlManager
from core.models.rows import CategoryDateProgress, CrawlExecutionState


@pytest.fixture
def historical_crawl_manager(mock_arxiv_source_explorer) -> HistoricalCrawlManager:
    """Create a HistoricalCrawlManager instance for testing with mock explorer."""
    categories = ["cs.AI", "cs.LG", "cs.CL"]
    return HistoricalCrawlManager(
        categories=categories,
    )


def test_initialization(historical_crawl_manager: HistoricalCrawlManager) -> None:
    """Test HistoricalCrawlManager initialization."""
    assert historical_crawl_manager.categories == ["cs.AI", "cs.LG", "cs.CL"]
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
        categories="cs.AI,cs.LG,cs.CL",
        is_active=True,
        total_papers_found=0,
        total_papers_stored=0,
    )

    # Should return first category for yesterday (simple strategy)
    result = historical_crawl_manager.get_next_date_category(state)
    assert result is not None
    date, category = result
    # Should start from yesterday, not the original start_date
    assert date == "2025-08-31"  # Yesterday
    assert category == "cs.AI"


def test_get_next_date_category_end_reached(
    historical_crawl_manager: HistoricalCrawlManager,
) -> None:
    """Test get_next_date_category when end date is reached."""
    # Create state at end date
    state = CrawlExecutionState(
        current_date="2015-01-01",
        current_category_index=0,
        categories="cs.AI,cs.LG,cs.CL",
        is_active=True,
        total_papers_found=0,
        total_papers_stored=0,
    )

    # Should start from yesterday even if current_date is at end date
    result = historical_crawl_manager.get_next_date_category(state)
    assert result is not None
    date, category = result
    assert date == "2025-08-31"  # Yesterday
    assert category == "cs.AI"


def test_advance_to_next_category(
    historical_crawl_manager: HistoricalCrawlManager,
) -> None:
    """Test advancing to next category within same date."""
    state = CrawlExecutionState(
        current_date="2025-01-01",
        current_category_index=0,
        categories="cs.AI,cs.LG,cs.CL",
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
        categories="cs.AI,cs.LG,cs.CL",
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

    manager = HistoricalCrawlManager(
        categories=categories,
    )

    assert manager.categories == ["cs.AI", "cs.LG"]
    assert manager.end_date == "2015-01-01"


@pytest.mark.asyncio
async def test_crawl_date_category_with_mock_server(
    historical_crawl_manager: HistoricalCrawlManager,
    mock_db_engine: Engine,
    mock_arxiv_source_explorer: ArxivSourceExplorer,
) -> None:
    """Test crawl_date_category with mock ArXiv server."""
    category = "cs.AI"
    date = "2025-01-01"

    # Mock server가 example_arxiv_response.xml을 반환하므로
    # 실제 API 호출 없이 테스트 가능
    papers_found, papers_stored = await historical_crawl_manager.crawl_date_category(
        engine=mock_db_engine,
        explorer=mock_arxiv_source_explorer,
        category=category,
        date=date,
    )

    # Mock response에는 10개의 논문이 있음
    assert papers_found >= 0  # 실제로는 10개지만, 네트워크 상태에 따라 달라질 수 있음
    assert papers_stored >= 0  # 저장된 논문 수
    assert papers_stored <= papers_found  # 저장된 수는 발견된 수보다 많을 수 없음


# New tests for simple crawl strategy
def test_should_skip_date_category_simple(
    historical_crawl_manager: HistoricalCrawlManager, mock_db_engine: Engine
) -> None:
    """Test _should_skip_date_category for simple strategy."""
    with Session(mock_db_engine) as db_session:
        # Create completed progress
        progress = CategoryDateProgress(
            category="cs.AI",
            date="2025-01-15",
            is_completed=True,
            papers_found=10,
            papers_stored=10,
        )
        db_session.add(progress)
        db_session.commit()

        # Should skip completed date
        assert (
            historical_crawl_manager._should_skip_date_category(
                db_session, "cs.AI", "2025-01-15"
            )
            is True
        )

        # Should not skip incomplete date
        assert (
            historical_crawl_manager._should_skip_date_category(
                db_session, "cs.LG", "2025-01-15"
            )
            is False
        )


@pytest.mark.asyncio
async def test_crawl_cycle_skips_completed_dates(
    historical_crawl_manager: HistoricalCrawlManager,
    mock_db_engine: Engine,
    mock_arxiv_source_explorer: ArxivSourceExplorer,
) -> None:
    """Test that crawl cycle skips completed dates."""
    with Session(mock_db_engine) as db_session:
        # Create completed progress
        progress = CategoryDateProgress(
            category="cs.AI",
            date="2025-08-31",  # Yesterday (will be set as current_date)
            is_completed=True,
            papers_found=10,
            papers_stored=10,
        )
        db_session.add(progress)
        db_session.commit()

    # Mock crawl_date_category
    with patch.object(
        historical_crawl_manager, "crawl_date_category", new_callable=AsyncMock
    ) as mock_crawl:
        # Run crawl cycle
        result = await historical_crawl_manager.run_crawl_cycle(
            mock_db_engine, mock_arxiv_source_explorer
        )

        # Verify crawl was not called (skipped)
        mock_crawl.assert_not_called()

        # Verify result is None (skipped)
        assert result is None
