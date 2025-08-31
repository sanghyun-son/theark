"""Tests for CrawlStateManager."""

from datetime import datetime, timedelta

import pytest

from core.extractors.concrete.crawl_state_manager import CrawlStateManager


@pytest.fixture
def state_manager(mock_db_engine):
    """CrawlStateManager instance with test engine."""
    return CrawlStateManager(mock_db_engine)


def test_crawl_state_manager_initialization(state_manager, mock_db_engine):
    """Test CrawlStateManager initialization."""
    assert state_manager.engine == mock_db_engine


def test_get_or_create_state_new(state_manager):
    """Test getting or creating state when none exists."""
    result = state_manager.get_or_create_state()

    # Verify result is a CrawlExecutionState
    assert result is not None
    assert result.last_execution_date is not None
    assert result.historical_crawl_date is not None
    assert result.historical_crawl_index == 0
    assert result.today_crawler_active is True
    assert result.historical_crawler_active is True


def test_get_or_create_state_existing(state_manager):
    """Test getting existing state."""
    # Create state first
    state1 = state_manager.get_or_create_state()

    # Get state again
    state2 = state_manager.get_or_create_state()

    # Verify same state is returned
    assert state1.state_id == state2.state_id
    assert state1.last_execution_date == state2.last_execution_date


def test_update_last_execution_date(state_manager):
    """Test updating last execution date."""
    state = state_manager.get_or_create_state()
    original_date = state.last_execution_date

    # Update date to a different date
    new_date = "2025-09-01"
    state_manager.update_last_execution_date(new_date)

    # Verify update
    updated_state = state_manager.get_or_create_state()
    assert updated_state.last_execution_date == new_date
    assert updated_state.last_execution_date != original_date


def test_update_historical_crawl_progress(state_manager):
    """Test updating historical crawl progress."""
    state = state_manager.get_or_create_state()
    original_date = state.historical_crawl_date
    original_index = state.historical_crawl_index

    # Update progress
    new_date = "2025-08-28"
    new_index = 10
    state_manager.update_historical_crawl_progress(new_date, new_index)

    # Verify update
    updated_state = state_manager.get_or_create_state()
    assert updated_state.historical_crawl_date == new_date
    assert updated_state.historical_crawl_index == new_index
    assert updated_state.historical_crawl_date != original_date
    assert updated_state.historical_crawl_index != original_index


def test_set_crawler_active_today(state_manager):
    """Test setting today crawler active status."""
    state = state_manager.get_or_create_state()
    original_status = state.today_crawler_active

    # Toggle status
    new_status = not original_status
    state_manager.set_crawler_active("today", new_status)

    # Verify update
    updated_state = state_manager.get_or_create_state()
    assert updated_state.today_crawler_active == new_status
    assert updated_state.today_crawler_active != original_status


def test_set_crawler_active_historical(state_manager):
    """Test setting historical crawler active status."""
    state = state_manager.get_or_create_state()
    original_status = state.historical_crawler_active

    # Toggle status
    new_status = not original_status
    state_manager.set_crawler_active("historical", new_status)

    # Verify update
    updated_state = state_manager.get_or_create_state()
    assert updated_state.historical_crawler_active == new_status
    assert updated_state.historical_crawler_active != original_status


def test_set_crawler_active_invalid_type(state_manager):
    """Test setting crawler active with invalid type."""
    with pytest.raises(ValueError, match="Invalid crawler type: invalid"):
        state_manager.set_crawler_active("invalid", True)


def test_get_historical_crawl_range(state_manager):
    """Test getting historical crawl range."""
    start_date, end_date = state_manager.get_historical_crawl_range()

    # Verify date format
    assert len(start_date) == 10  # YYYY-MM-DD
    assert len(end_date) == 10  # YYYY-MM-DD
    assert start_date.count("-") == 2
    assert end_date.count("-") == 2

    # Verify start_date is yesterday
    yesterday = (datetime.now() - timedelta(days=1)).strftime("%Y-%m-%d")
    assert start_date == yesterday


def test_is_crawler_active_today(state_manager):
    """Test checking if today crawler is active."""
    result = state_manager.is_crawler_active("today")
    assert isinstance(result, bool)


def test_is_crawler_active_historical(state_manager):
    """Test checking if historical crawler is active."""
    result = state_manager.is_crawler_active("historical")
    assert isinstance(result, bool)


def test_is_crawler_active_invalid_type(state_manager):
    """Test checking crawler active with invalid type."""
    with pytest.raises(ValueError, match="Invalid crawler type: invalid"):
        state_manager.is_crawler_active("invalid")


def test_get_current_historical_crawl_state(state_manager):
    """Test getting current historical crawl state."""
    date, index = state_manager.get_current_historical_crawl_state()

    # Verify date format
    assert len(date) == 10  # YYYY-MM-DD
    assert date.count("-") == 2

    # Verify index is integer
    assert isinstance(index, int)
    assert index >= 0
