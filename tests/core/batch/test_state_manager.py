"""Tests for batch state manager."""

from unittest.mock import Mock

from sqlmodel import Session
from sqlalchemy.engine import Engine

from core.batch.state_manager import BatchStateManager
from core.database.repository.paper import PaperRepository
from core.models.batch import BatchItemCreate
from core.models.rows import Paper


def test_get_pending_summaries_success(
    mock_db_engine: Engine,
    paper_repo: PaperRepository,
    saved_papers: list[Paper],
) -> None:
    """Test successful retrieval of pending summaries."""
    # Arrange - Use saved_papers fixture which includes papers with "batched" status
    # The fixture creates 2 papers with "batched" status and 1 with "done" status
    batch_state_manager = BatchStateManager()

    # Act
    result = batch_state_manager.get_pending_summaries(mock_db_engine)

    # Assert - Only papers with "batched" status should be returned
    assert len(result) == 2
    # Check that both papers are returned (order may vary due to ORDER BY published_at DESC)
    paper_ids = {result[0].paper_id, result[1].paper_id}
    arxiv_ids = {result[0].arxiv_id, result[1].arxiv_id}
    assert paper_ids == {saved_papers[0].paper_id, saved_papers[1].paper_id}
    assert arxiv_ids == {"2201.00001", "2201.00002"}


def test_get_pending_summaries_empty_result(
    mock_db_engine: Engine,
    paper_repo: PaperRepository,
) -> None:
    """Test when no papers need summarization."""
    # Arrange - Empty database (no papers with "batched" status)
    # The mock_db_session starts with an empty database
    batch_state_manager = BatchStateManager()

    # Act
    result = batch_state_manager.get_pending_summaries(mock_db_engine)

    # Assert
    assert result == []


def test_get_pending_summaries_database_error() -> None:
    """Test handling of database errors."""
    batch_state_manager = BatchStateManager()

    mock_db = Mock(spec=Session)
    mock_db.exec.side_effect = Exception("DB Error")

    result = batch_state_manager.get_pending_summaries(mock_db)
    assert result == []


def test_create_batch_record_success(
    mock_db_engine: Engine,
) -> None:
    """Test successful creation of batch record."""
    batch_state_manager = BatchStateManager()

    batch_state_manager.create_batch_record(
        mock_db_engine,
        batch_id="test_batch_123",
        input_file_id="file_123",
        completion_window="24h",
        endpoint="/v1/chat/completions",
        metadata={"test": "data"},
    )


def test_create_batch_record_without_metadata(
    mock_db_engine: Engine,
) -> None:
    """Test creation of batch record without metadata."""
    batch_state_manager = BatchStateManager()

    batch_state_manager.create_batch_record(
        mock_db_engine,
        batch_id="test_batch_456",
        input_file_id="file_456",
    )


def test_update_batch_status_success(
    mock_db_engine: Engine,
) -> None:
    """Test successful update of batch status."""
    batch_state_manager = BatchStateManager()

    batch_state_manager.create_batch_record(
        mock_db_engine,
        batch_id="test_batch_update",
        input_file_id="file_123",
    )

    batch_state_manager.update_batch_status(
        mock_db_engine,
        batch_id="test_batch_update",
        status="in_progress",
        error_file_id=None,
    )


def test_update_batch_status_with_error_file(
    mock_db_engine: Engine,
) -> None:
    """Test updating batch status with error file."""
    batch_state_manager = BatchStateManager()

    batch_state_manager.create_batch_record(
        mock_db_engine,
        batch_id="test_batch_error",
        input_file_id="file_123",
    )

    batch_state_manager.update_batch_status(
        mock_db_engine,
        batch_id="test_batch_error",
        status="failed",
        error_file_id="error_789",
    )


def test_add_batch_items_success(
    mock_db_engine: Engine,
    saved_papers: list[Paper],
) -> None:
    """Test successful addition of batch items."""
    batch_state_manager = BatchStateManager()

    batch_state_manager.create_batch_record(
        mock_db_engine,
        batch_id="test_batch_items",
        input_file_id="file_123",
    )

    paper_id_1 = saved_papers[0].paper_id
    paper_id_2 = saved_papers[1].paper_id
    assert paper_id_1 is not None
    assert paper_id_2 is not None

    items = [
        BatchItemCreate(
            paper_id=paper_id_1,
            input_data='{"messages": [{"role": "user", "content": "Summarize this paper"}]}',
        ),
        BatchItemCreate(
            paper_id=paper_id_2,
            input_data='{"messages": [{"role": "user", "content": "Summarize this paper"}]}',
        ),
    ]
    batch_state_manager.add_batch_items(mock_db_engine, "test_batch_items", items)
    result = batch_state_manager.get_batch_items(mock_db_engine, "test_batch_items")
    assert len(result) == 2


def test_add_batch_items_empty_list(
    mock_db_engine: Engine,
) -> None:
    """Test adding empty list of batch items."""
    batch_state_manager = BatchStateManager()

    batch_state_manager.create_batch_record(
        mock_db_engine,
        batch_id="test_batch_empty",
        input_file_id="file_123",
    )

    batch_state_manager.add_batch_items(mock_db_engine, "test_batch_empty", [])

    result = batch_state_manager.get_batch_items(mock_db_engine, "test_batch_empty")
    assert len(result) == 0


def test_update_batch_item_status_success(
    mock_db_engine: Engine,
    saved_papers: list[Paper],
) -> None:
    """Test successful update of batch item status."""
    batch_state_manager = BatchStateManager()

    batch_state_manager.create_batch_record(
        mock_db_engine,
        batch_id="test_batch_item_update",
        input_file_id="file_123",
    )

    paper_id = saved_papers[0].paper_id
    assert paper_id is not None

    items = [
        BatchItemCreate(
            paper_id=paper_id,
            input_data='{"messages": [{"role": "user", "content": "Summarize this paper"}]}',
        ),
    ]
    batch_state_manager.add_batch_items(mock_db_engine, "test_batch_item_update", items)

    batch_state_manager.update_batch_item_status(
        mock_db_engine,
        batch_id="test_batch_item_update",
        paper_id=paper_id,
        status="completed",
    )

    result = batch_state_manager.get_batch_items(
        mock_db_engine, "test_batch_item_update"
    )
    assert len(result) == 1


def test_update_batch_item_status_with_error(
    mock_db_engine: Engine,
    saved_papers: list[Paper],
) -> None:
    """Test updating batch item status with error."""
    batch_state_manager = BatchStateManager()

    batch_state_manager.create_batch_record(
        mock_db_engine,
        batch_id="test_batch_item_error",
        input_file_id="file_123",
    )

    paper_id = saved_papers[0].paper_id
    assert paper_id is not None

    items = [
        BatchItemCreate(
            paper_id=paper_id,
            input_data='{"messages": [{"role": "user", "content": "Summarize this paper"}]}',
        ),
    ]
    batch_state_manager.add_batch_items(mock_db_engine, "test_batch_item_error", items)

    batch_state_manager.update_batch_item_status(
        mock_db_engine,
        batch_id="test_batch_item_error",
        paper_id=paper_id,
        status="failed",
        error_message="Processing failed due to invalid input",
    )

    result = batch_state_manager.get_batch_items(
        mock_db_engine, "test_batch_item_error"
    )
    assert len(result) == 1


def test_get_active_batches_success(
    mock_db_engine: Engine,
) -> None:
    """Test successful retrieval of active batches."""
    batch_state_manager = BatchStateManager()

    result = batch_state_manager.get_active_batches(mock_db_engine)
    assert result == []


def test_get_active_batches_empty_result(
    mock_db_engine: Engine,
) -> None:
    """Test when no active batches exist."""
    batch_state_manager = BatchStateManager()

    result = batch_state_manager.get_active_batches(mock_db_engine)
    assert result == []


def test_get_active_batches_database_error() -> None:
    """Test handling of database errors for active batches."""
    batch_state_manager = BatchStateManager()

    mock_db = Mock(spec=Session)
    mock_db.exec.side_effect = Exception("DB Error")

    result = batch_state_manager.get_active_batches(mock_db)
    assert result == []
