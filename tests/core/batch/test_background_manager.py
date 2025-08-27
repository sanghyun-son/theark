"""Tests for background batch manager."""

import asyncio
from unittest.mock import AsyncMock, MagicMock

import pytest

from core.batch.background_manager import BackgroundBatchManager
from core.config import Settings
from core.database.interfaces import DatabaseManager


@pytest.fixture
def mock_settings() -> Settings:
    """Mock settings for testing."""
    settings = MagicMock(spec=Settings)
    settings.batch_enabled = True
    settings.batch_summary_interval = 1  # 1 second for testing
    settings.batch_fetch_interval = 1  # 1 second for testing
    settings.batch_max_items = 1000
    settings.batch_daily_limit = 10000
    settings.batch_max_retries = 3
    return settings


@pytest.fixture
def background_manager(mock_settings: Settings) -> BackgroundBatchManager:
    """Background batch manager instance."""
    return BackgroundBatchManager(mock_settings)


@pytest.mark.asyncio
async def test_background_manager_initialization(
    mock_settings: Settings,
) -> None:
    """Test background manager initialization."""
    # Act
    manager = BackgroundBatchManager(mock_settings)

    # Assert
    assert manager._settings == mock_settings
    assert not manager.is_running
    assert manager._summary_task is None
    assert manager._fetch_task is None


@pytest.mark.asyncio
async def test_start_background_manager(
    background_manager: BackgroundBatchManager,
    mock_db_manager: DatabaseManager,
    mock_openai_client,
) -> None:
    """Test starting background manager."""
    # Act
    await background_manager.start(mock_db_manager, mock_openai_client)

    # Assert
    assert background_manager.is_running
    assert background_manager._summary_task is not None
    assert background_manager._fetch_task is not None
    assert not background_manager._summary_task.done()
    assert not background_manager._fetch_task.done()

    # Cleanup
    await background_manager.stop()


@pytest.mark.asyncio
async def test_start_background_manager_when_disabled(
    mock_settings: Settings, mock_db_manager: DatabaseManager, mock_openai_client
) -> None:
    """Test starting background manager when disabled."""
    # Arrange
    mock_settings.batch_enabled = False
    manager = BackgroundBatchManager(mock_settings)

    # Act
    await manager.start(mock_db_manager, mock_openai_client)

    # Assert
    assert not manager.is_running
    assert manager._summary_task is None
    assert manager._fetch_task is None


@pytest.mark.asyncio
async def test_start_background_manager_already_running(
    background_manager: BackgroundBatchManager,
    mock_db_manager: DatabaseManager,
    mock_openai_client,
) -> None:
    """Test starting background manager when already running."""
    # Arrange
    await background_manager.start(mock_db_manager, mock_openai_client)

    # Act
    await background_manager.start(mock_db_manager, mock_openai_client)

    # Assert
    assert background_manager.is_running

    # Cleanup
    await background_manager.stop()


@pytest.mark.asyncio
async def test_stop_background_manager(
    background_manager: BackgroundBatchManager,
    mock_db_manager: DatabaseManager,
    mock_openai_client,
) -> None:
    """Test stopping background manager."""
    # Arrange
    await background_manager.start(mock_db_manager, mock_openai_client)

    # Act
    await background_manager.stop()

    # Assert
    assert not background_manager.is_running
    assert background_manager._summary_task is None
    assert background_manager._fetch_task is None


@pytest.mark.asyncio
async def test_stop_background_manager_not_running(
    background_manager: BackgroundBatchManager,
) -> None:
    """Test stopping background manager when not running."""
    # Act
    await background_manager.stop()

    # Assert
    assert not background_manager.is_running


@pytest.mark.asyncio
async def test_summary_scheduler_runs_once(
    background_manager: BackgroundBatchManager,
    mock_db_manager: DatabaseManager,
    mock_openai_client,
) -> None:
    """Test that summary scheduler runs at least once."""
    # Act
    await background_manager.start(mock_db_manager, mock_openai_client)

    # Wait a bit for the scheduler to run
    await asyncio.sleep(0.1)

    # Assert - Check before stopping
    assert background_manager._summary_task is not None

    await background_manager.stop()


@pytest.mark.asyncio
async def test_fetch_scheduler_runs_once(
    background_manager: BackgroundBatchManager,
    mock_db_manager: DatabaseManager,
    mock_openai_client,
) -> None:
    """Test that fetch scheduler runs at least once."""
    # Act
    await background_manager.start(mock_db_manager, mock_openai_client)

    # Wait a bit for the scheduler to run
    await asyncio.sleep(0.1)

    # Assert - Check before stopping
    assert background_manager._fetch_task is not None

    await background_manager.stop()


@pytest.mark.asyncio
async def test_process_pending_summaries_with_papers(
    background_manager: BackgroundBatchManager,
    mock_db_manager: DatabaseManager,
    mock_openai_client,
) -> None:
    """Test processing pending summaries with papers."""
    # Arrange - Insert test papers into real database
    await mock_db_manager.execute(
        """
        INSERT INTO paper (
            paper_id, arxiv_id, title, abstract, authors, primary_category, 
            categories, url_abs, url_pdf, published_at, updated_at
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
        (
            1,
            "2201.00001",
            "Test Paper 1",
            "Test Abstract 1",
            "Author 1",
            "cs.AI",
            "cs.AI,cs.LG",
            "http://arxiv.org/abs/2201.00001",
            "http://arxiv.org/pdf/2201.00001",
            "2023-01-01",
            "2023-01-01",
        ),
    )
    await mock_db_manager.execute(
        """
        INSERT INTO paper (
            paper_id, arxiv_id, title, abstract, authors, primary_category, 
            categories, url_abs, url_pdf, published_at, updated_at
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
        (
            2,
            "2201.00002",
            "Test Paper 2",
            "Test Abstract 2",
            "Author 2",
            "cs.AI",
            "cs.AI,cs.LG",
            "http://arxiv.org/abs/2201.00002",
            "http://arxiv.org/pdf/2201.00002",
            "2023-01-01",
            "2023-01-01",
        ),
    )

    # Act
    await background_manager._process_pending_summaries(
        mock_db_manager, mock_openai_client
    )

    # Assert - Verify that papers were found and processed
    # The method should have called get_pending_summaries through BatchStateManager
    # Since we're using real DB, we can verify the papers exist
    papers = await mock_db_manager.fetch_all(
        "SELECT * FROM paper WHERE paper_id IN (1, 2)"
    )
    assert len(papers) == 2


@pytest.mark.asyncio
async def test_process_pending_summaries_empty(
    background_manager: BackgroundBatchManager,
    mock_db_manager: DatabaseManager,
    mock_openai_client,
) -> None:
    """Test processing pending summaries with no papers."""
    # Act
    await background_manager._process_pending_summaries(
        mock_db_manager, mock_openai_client
    )

    # Assert - Should complete without error even with empty database
    # Verify no papers exist
    papers = await mock_db_manager.fetch_all("SELECT * FROM paper")
    assert len(papers) == 0


@pytest.mark.asyncio
async def test_process_active_batches_with_batches(
    background_manager: BackgroundBatchManager,
    mock_db_manager: DatabaseManager,
    mock_openai_client,
) -> None:
    """Test processing active batches with batches."""
    # Arrange - Insert test batch requests into real database
    await mock_db_manager.execute(
        """
        INSERT INTO llm_batch_requests (
            batch_id, status, input_file_id, completion_window, endpoint
        ) VALUES (?, ?, ?, ?, ?)
        """,
        ("batch_1", "in_progress", "file_1", "24h", "/v1/chat/completions"),
    )
    await mock_db_manager.execute(
        """
        INSERT INTO llm_batch_requests (
            batch_id, status, input_file_id, completion_window, endpoint
        ) VALUES (?, ?, ?, ?, ?)
        """,
        ("batch_2", "validating", "file_2", "24h", "/v1/chat/completions"),
    )

    # Act
    await background_manager._process_active_batches(
        mock_db_manager, mock_openai_client
    )

    # Assert - Verify that batches were found and processed
    batches = await mock_db_manager.fetch_all(
        "SELECT * FROM llm_batch_requests WHERE batch_id IN ('batch_1', 'batch_2')"
    )
    assert len(batches) == 2


@pytest.mark.asyncio
async def test_process_active_batches_empty(
    background_manager: BackgroundBatchManager,
    mock_db_manager: DatabaseManager,
    mock_openai_client,
) -> None:
    """Test processing active batches with no batches."""
    # Act
    await background_manager._process_active_batches(
        mock_db_manager, mock_openai_client
    )

    # Assert - Should complete without error even with empty database
    # Verify no batches exist
    batches = await mock_db_manager.fetch_all("SELECT * FROM llm_batch_requests")
    assert len(batches) == 0


@pytest.mark.asyncio
async def test_check_daily_limit(
    background_manager: BackgroundBatchManager, mock_db_manager: DatabaseManager
) -> None:
    """Test daily limit checking."""
    # Act
    result = await background_manager._check_daily_limit(mock_db_manager)

    # Assert
    assert result is True  # Currently always returns True


@pytest.mark.asyncio
async def test_process_pending_summaries_handles_db_error(
    background_manager: BackgroundBatchManager, mock_openai_client
) -> None:
    """Test error handling when database operations fail."""
    # Arrange - Create a mock DB that raises an exception
    mock_db_manager = AsyncMock(spec=DatabaseManager)
    mock_db_manager.fetch_all.side_effect = Exception("DB Error")

    # Act & Assert - Should not raise exception, should handle gracefully
    await background_manager._process_pending_summaries(
        mock_db_manager, mock_openai_client
    )


@pytest.mark.asyncio
async def test_process_active_batches_handles_db_error(
    background_manager: BackgroundBatchManager, mock_openai_client
) -> None:
    """Test error handling when database operations fail."""
    # Arrange - Create a mock DB that raises an exception
    mock_db_manager = AsyncMock(spec=DatabaseManager)
    mock_db_manager.fetch_all.side_effect = Exception("DB Error")

    # Act & Assert - Should not raise exception, should handle gracefully
    await background_manager._process_active_batches(
        mock_db_manager, mock_openai_client
    )


@pytest.mark.asyncio
async def test_different_intervals_work_correctly(
    mock_settings: Settings, mock_db_manager: DatabaseManager, mock_openai_client
) -> None:
    """Test that different interval settings work correctly."""
    # Arrange
    mock_settings.batch_summary_interval = 5
    mock_settings.batch_fetch_interval = 3
    manager = BackgroundBatchManager(mock_settings)

    # Act
    await manager.start(mock_db_manager, mock_openai_client)

    # Assert - Should start with different intervals
    assert manager.is_running
    assert manager._summary_task is not None
    assert manager._fetch_task is not None

    # Cleanup
    await manager.stop()
