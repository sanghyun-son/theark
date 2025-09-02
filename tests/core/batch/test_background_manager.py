"""Tests for background batch manager."""

import asyncio
from unittest.mock import Mock, patch

import pytest
from sqlalchemy.engine import Engine

from core.batch.background_manager import BackgroundBatchManager
from core.database.repository.paper import PaperRepository
from core.llm.openai_client import UnifiedOpenAIClient
from core.models.rows import Paper


@pytest.mark.asyncio
async def test_background_manager_life_cycle(
    mock_background_manager: BackgroundBatchManager,
    mock_db_engine: Engine,
    mock_openai_client,
) -> None:
    """Test background manager life cycle."""

    assert not mock_background_manager.is_running

    await mock_background_manager.start(mock_db_engine, mock_openai_client)
    assert mock_background_manager.is_running

    assert mock_background_manager._summary_task is not None
    assert mock_background_manager._fetch_task is not None
    assert not mock_background_manager._summary_task.done()
    assert not mock_background_manager._fetch_task.done()

    await mock_background_manager.stop()
    assert not mock_background_manager.is_running
    assert mock_background_manager._summary_task is None
    assert mock_background_manager._fetch_task is None


@pytest.mark.asyncio
async def test_start_background_manager_when_disabled(
    mock_background_manager: BackgroundBatchManager,
    mock_db_engine: Engine,
    mock_openai_client,
) -> None:

    mock_background_manager._batch_enabled = False
    await mock_background_manager.start(mock_db_engine, mock_openai_client)

    assert not mock_background_manager.is_running
    assert mock_background_manager._summary_task is None
    assert mock_background_manager._fetch_task is None


@pytest.mark.asyncio
async def test_start_background_manager_already_running(
    mock_background_manager: BackgroundBatchManager,
    mock_db_engine: Engine,
    mock_openai_client,
) -> None:

    await mock_background_manager.start(mock_db_engine, mock_openai_client)
    await mock_background_manager.start(mock_db_engine, mock_openai_client)
    assert mock_background_manager.is_running
    await mock_background_manager.stop()


@pytest.mark.asyncio
async def test_stop_background_manager_not_running(
    mock_background_manager: BackgroundBatchManager,
) -> None:

    await mock_background_manager.stop()
    assert not mock_background_manager.is_running


@pytest.mark.asyncio
async def test_summary_scheduler_runs_once(
    mock_background_manager: BackgroundBatchManager,
    mock_db_engine: Engine,
    mock_openai_client: UnifiedOpenAIClient,
) -> None:
    """Test that summary scheduler runs at least once."""

    with patch.object(
        mock_background_manager, "_process_pending_summaries"
    ) as mock_process:
        await mock_background_manager.start(mock_db_engine, mock_openai_client)

        await asyncio.sleep(0.1)

        mock_process.assert_called_once_with(mock_db_engine, mock_openai_client)
        assert mock_background_manager._summary_task is not None

    await mock_background_manager.stop()


@pytest.mark.asyncio
async def test_fetch_scheduler_runs_once(
    mock_background_manager: BackgroundBatchManager,
    mock_db_engine: Engine,
    mock_openai_client: UnifiedOpenAIClient,
) -> None:
    """Test that fetch scheduler runs at least once."""

    with patch.object(
        mock_background_manager, "_process_active_batches"
    ) as mock_process:

        await mock_background_manager.start(mock_db_engine, mock_openai_client)

        await asyncio.sleep(0.1)

        mock_process.assert_called_once_with(mock_db_engine, mock_openai_client)
        assert mock_background_manager._fetch_task is not None

    await mock_background_manager.stop()


@pytest.mark.asyncio
async def test_process_pending_summaries_with_papers(
    mock_background_manager: BackgroundBatchManager,
    mock_db_engine: Engine,
    mock_openai_client: UnifiedOpenAIClient,
    paper_repo: PaperRepository,
    saved_papers: list[Paper],
) -> None:
    """Test processing pending summaries with papers."""
    # Arrange - Use saved_papers fixture which includes papers with "batched" status
    # The fixture creates 2 papers with "batched" status and 1 with "done" status

    # Act
    await mock_background_manager._process_pending_summaries(
        mock_db_engine, mock_openai_client
    )

    # Assert - Only papers with "batched" status should be processed
    papers = paper_repo.get_papers_by_status("processing")
    assert len(papers) == 2

    for paper in papers:
        assert paper.summary_status == "processing"


@pytest.mark.asyncio
async def test_process_pending_summaries_empty(
    mock_background_manager: BackgroundBatchManager,
    mock_db_engine: Engine,
    mock_openai_client: UnifiedOpenAIClient,
    paper_repo: PaperRepository,
) -> None:
    """Test processing pending summaries with no papers."""
    # Act - No papers in database, so should process empty list
    await mock_background_manager._process_pending_summaries(
        mock_db_engine, mock_openai_client
    )

    # Assert - Should complete without error even with empty database
    papers = paper_repo.get_papers_by_status("processing")
    assert len(papers) == 0  # No papers should be marked as processing


@pytest.mark.asyncio
async def test_process_active_batches_with_batches(
    mock_background_manager: BackgroundBatchManager,
    mock_db_engine: Engine,
    mock_openai_client: UnifiedOpenAIClient,
) -> None:
    """Test processing active batches with batches."""
    # Arrange - Note: This test needs proper batch repository implementation
    # For now, we'll just test that the method completes without error
    # TODO: Implement proper batch repository and update this test

    # Act
    await mock_background_manager._process_active_batches(
        mock_db_engine, mock_openai_client
    )

    # Assert - Verify that batches were found and processed
    # Note: This test needs to be updated to use proper repository methods
    # For now, we'll just verify the method completes without error
    # TODO: Implement proper batch repository and update this test


@pytest.mark.asyncio
async def test_process_active_batches_empty(
    mock_background_manager: BackgroundBatchManager,
    mock_db_engine: Engine,
    mock_openai_client: UnifiedOpenAIClient,
) -> None:
    """Test processing active batches with no batches."""
    # Act
    await mock_background_manager._process_active_batches(
        mock_db_engine, mock_openai_client
    )

    # Assert - Should complete without error even with empty database
    # Note: This test needs to be updated to use proper repository methods
    # For now, we'll just verify the method completes without error
    # TODO: Implement proper batch repository and update this test


@pytest.mark.asyncio
async def test_check_daily_limit(
    mock_background_manager: BackgroundBatchManager,
    mock_db_engine: Engine,
) -> None:
    """Test daily limit checking."""
    # Act
    result = await mock_background_manager._check_daily_limit(mock_db_engine)

    # Assert
    assert result is True  # Currently always returns True


@pytest.mark.asyncio
async def test_process_pending_summaries_handles_db_error(
    mock_background_manager: BackgroundBatchManager,
    mock_openai_client: UnifiedOpenAIClient,
) -> None:
    """Test error handling when database operations fail."""
    # Arrange - Create a mock DB that raises an exception
    mock_db_engine = Mock(spec=Engine)
    # Mock the LLMBatchRepository to raise an exception
    with patch(
        "core.database.repository.llm_batch.LLMBatchRepository.get_pending_summaries"
    ) as mock_get:
        mock_get.side_effect = Exception("DB Error")

        # Act & Assert - Should not raise exception, should handle gracefully
        await mock_background_manager._process_pending_summaries(
            mock_db_engine, mock_openai_client
        )


@pytest.mark.asyncio
async def test_process_active_batches_handles_db_error(
    mock_background_manager: BackgroundBatchManager,
    mock_openai_client: UnifiedOpenAIClient,
) -> None:
    """Test error handling when database operations fail."""
    # Arrange - Create a mock DB that raises an exception
    mock_background_manager._state_manager.get_active_batches = Mock(
        side_effect=Exception("DB Error")
    )
    mock_db_engine = Mock(spec=Engine)
    await mock_background_manager._process_active_batches(
        mock_db_engine,
        mock_openai_client,
    )


@pytest.mark.asyncio
async def test_different_intervals_work_correctly(
    mock_background_manager: BackgroundBatchManager,
    mock_db_engine: Engine,
    mock_openai_client: UnifiedOpenAIClient,
) -> None:
    """Test that different interval settings work correctly."""
    # Arrange - Override intervals for this specific test
    mock_background_manager._batch_summary_interval = 5
    mock_background_manager._batch_fetch_interval = 3

    # Act
    await mock_background_manager.start(mock_db_engine, mock_openai_client)

    # Assert - Should start with different intervals
    assert mock_background_manager.is_running
    assert mock_background_manager._summary_task is not None
    assert mock_background_manager._fetch_task is not None

    # Cleanup
    await mock_background_manager.stop()
