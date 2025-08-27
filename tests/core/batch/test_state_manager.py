"""Tests for batch state manager."""

from typing import Any

import pytest
from unittest.mock import AsyncMock

from core.batch.state_manager import BatchStateManager
from core.database.interfaces import DatabaseManager


@pytest.fixture
def batch_state_manager() -> BatchStateManager:
    """Batch state manager instance."""
    return BatchStateManager()


@pytest.fixture
def sample_papers() -> list[dict[str, Any]]:
    """Sample papers for testing."""
    return [
        {
            "paper_id": 1,
            "arxiv_id": "2205.14135",
            "title": "Test Paper 1",
            "abstract": "This is a test abstract for paper 1",
            "published_at": "2022-05-28",
        },
        {
            "paper_id": 2,
            "arxiv_id": "2205.14136",
            "title": "Test Paper 2",
            "abstract": "This is a test abstract for paper 2",
            "published_at": "2022-05-29",
        },
    ]


@pytest.fixture
def sample_batches() -> list[dict[str, Any]]:
    """Sample batch requests for testing."""
    return [
        {
            "batch_id": "batch_123",
            "status": "in_progress",
            "input_file_id": "file_123",
            "output_file_id": None,
            "created_at": "2024-01-01T10:00:00Z",
            "in_progress_at": "2024-01-01T10:05:00Z",
        },
        {
            "batch_id": "batch_456",
            "status": "validating",
            "input_file_id": "file_456",
            "output_file_id": None,
            "created_at": "2024-01-01T11:00:00Z",
            "in_progress_at": None,
        },
    ]


@pytest.mark.asyncio
async def test_get_pending_summaries_success(
    batch_state_manager: BatchStateManager, mock_db_manager: DatabaseManager
) -> None:
    """Test successful retrieval of pending summaries."""
    # Arrange - Insert test papers
    await mock_db_manager.execute(
        """
        INSERT INTO paper (paper_id, arxiv_id, title, abstract, primary_category, categories, authors, url_abs, url_pdf, published_at, updated_at, summary_status)
        VALUES (1, '2205.14135', 'Test Paper 1', 'This is a test abstract for paper 1', 'cs.AI', 'cs.AI,cs.LG', 'Author 1, Author 2', 'https://arxiv.org/abs/2205.14135', 'https://arxiv.org/pdf/2205.14135', '2022-05-28', '2022-05-28', 'batched'),
               (2, '2205.14136', 'Test Paper 2', 'This is a test abstract for paper 2', 'cs.AI', 'cs.AI,cs.CL', 'Author 3, Author 4', 'https://arxiv.org/abs/2205.14136', 'https://arxiv.org/pdf/2205.14136', '2022-05-29', '2022-05-29', 'batched')
        """
    )

    # Act
    result = await batch_state_manager.get_pending_summaries(mock_db_manager)

    # Assert
    assert len(result) == 2
    # Check that both papers are returned (order may vary due to ORDER BY published_at DESC)
    paper_ids = {result[0]["paper_id"], result[1]["paper_id"]}
    arxiv_ids = {result[0]["arxiv_id"], result[1]["arxiv_id"]}
    assert paper_ids == {1, 2}
    assert arxiv_ids == {"2205.14135", "2205.14136"}


@pytest.mark.asyncio
async def test_get_pending_summaries_empty_result(
    batch_state_manager: BatchStateManager, mock_db_manager: DatabaseManager
) -> None:
    """Test when no papers need summarization."""
    # Act
    result = await batch_state_manager.get_pending_summaries(mock_db_manager)

    # Assert
    assert result == []


@pytest.mark.asyncio
async def test_get_pending_summaries_database_error(
    batch_state_manager: BatchStateManager,
) -> None:
    """Test handling of database errors."""
    # Arrange
    mock_db = AsyncMock(spec=DatabaseManager)
    mock_db.fetch_all.side_effect = Exception("Database connection failed")

    # Act & Assert
    with pytest.raises(Exception, match="Database connection failed"):
        await batch_state_manager.get_pending_summaries(mock_db)

    mock_db.fetch_all.assert_called_once()


@pytest.mark.asyncio
async def test_create_batch_record_success(
    batch_state_manager: BatchStateManager, mock_db_manager: DatabaseManager
) -> None:
    """Test successful creation of batch record."""
    # Act
    await batch_state_manager.create_batch_record(
        mock_db_manager,
        batch_id="test_batch_123",
        input_file_id="file_123",
        completion_window="24h",
        endpoint="/v1/chat/completions",
        metadata={"test": "data"},
    )

    # Assert - Verify the record was created
    result = await mock_db_manager.fetch_all(
        "SELECT * FROM llm_batch_requests WHERE batch_id = ?", ("test_batch_123",)
    )
    assert len(result) == 1
    assert result[0]["batch_id"] == "test_batch_123"
    assert result[0]["input_file_id"] == "file_123"
    assert result[0]["completion_window"] == "24h"
    assert result[0]["endpoint"] == "/v1/chat/completions"
    assert result[0]["status"] == "validating"  # Default status


@pytest.mark.asyncio
async def test_create_batch_record_without_metadata(
    batch_state_manager: BatchStateManager, mock_db_manager: DatabaseManager
) -> None:
    """Test creation of batch record without metadata."""
    # Act
    await batch_state_manager.create_batch_record(
        mock_db_manager,
        batch_id="test_batch_456",
        input_file_id="file_456",
    )

    # Assert - Verify the record was created with defaults
    result = await mock_db_manager.fetch_all(
        "SELECT * FROM llm_batch_requests WHERE batch_id = ?", ("test_batch_456",)
    )
    assert len(result) == 1
    assert result[0]["batch_id"] == "test_batch_456"
    assert result[0]["input_file_id"] == "file_456"
    assert result[0]["completion_window"] == "24h"  # Default
    assert result[0]["endpoint"] == "/v1/chat/completions"  # Default
    assert result[0]["metadata"] is None


@pytest.mark.asyncio
async def test_update_batch_status_success(
    batch_state_manager: BatchStateManager, mock_db_manager: DatabaseManager
) -> None:
    """Test successful update of batch status."""
    # Arrange - Create a batch record first
    await batch_state_manager.create_batch_record(
        mock_db_manager,
        batch_id="test_batch_update",
        input_file_id="file_123",
    )

    # Act - Update status
    await batch_state_manager.update_batch_status(
        mock_db_manager,
        batch_id="test_batch_update",
        status="in_progress",
        output_file_id="output_456",
        request_counts={"completed": 10, "failed": 2},
    )

    # Assert - Verify the status was updated
    result = await mock_db_manager.fetch_all(
        "SELECT * FROM llm_batch_requests WHERE batch_id = ?", ("test_batch_update",)
    )
    assert len(result) == 1
    assert result[0]["status"] == "in_progress"
    assert result[0]["output_file_id"] == "output_456"
    assert result[0]["request_counts"] == '{"completed": 10, "failed": 2}'


@pytest.mark.asyncio
async def test_update_batch_status_with_error_file(
    batch_state_manager: BatchStateManager, mock_db_manager: DatabaseManager
) -> None:
    """Test updating batch status with error file."""
    # Arrange - Create a batch record first
    await batch_state_manager.create_batch_record(
        mock_db_manager,
        batch_id="test_batch_error",
        input_file_id="file_123",
    )

    # Act - Update status to failed with error file
    await batch_state_manager.update_batch_status(
        mock_db_manager,
        batch_id="test_batch_error",
        status="failed",
        error_file_id="error_789",
    )

    # Assert - Verify the status was updated
    result = await mock_db_manager.fetch_all(
        "SELECT * FROM llm_batch_requests WHERE batch_id = ?", ("test_batch_error",)
    )
    assert len(result) == 1
    assert result[0]["status"] == "failed"
    assert result[0]["error_file_id"] == "error_789"
    assert result[0]["completed_at"] is not None  # Should be set for failed status


@pytest.mark.asyncio
async def test_add_batch_items_success(
    batch_state_manager: BatchStateManager, mock_db_manager: DatabaseManager
) -> None:
    """Test successful addition of batch items."""
    # Arrange - Create a batch record first
    await batch_state_manager.create_batch_record(
        mock_db_manager,
        batch_id="test_batch_items",
        input_file_id="file_123",
    )

    # Create test papers
    await mock_db_manager.execute(
        """
        INSERT INTO paper (paper_id, arxiv_id, title, abstract, primary_category, categories, authors, url_abs, url_pdf, published_at, updated_at)
        VALUES (1, '2205.14135', 'Test Paper 1', 'This is a test abstract for paper 1', 'cs.AI', 'cs.AI,cs.LG', 'Author 1, Author 2', 'https://arxiv.org/abs/2205.14135', 'https://arxiv.org/pdf/2205.14135', '2022-05-28', '2022-05-28'),
               (2, '2205.14136', 'Test Paper 2', 'This is a test abstract for paper 2', 'cs.AI', 'cs.AI,cs.CL', 'Author 3, Author 4', 'https://arxiv.org/abs/2205.14136', 'https://arxiv.org/pdf/2205.14136', '2022-05-29', '2022-05-29')
        """
    )

    # Act - Add batch items
    items = [
        {
            "paper_id": 1,
            "input_data": '{"messages": [{"role": "user", "content": "Summarize this paper"}]}',
        },
        {
            "paper_id": 2,
            "input_data": '{"messages": [{"role": "user", "content": "Summarize this paper"}]}',
        },
    ]
    await batch_state_manager.add_batch_items(
        mock_db_manager, "test_batch_items", items
    )

    # Assert - Verify items were added
    result = await batch_state_manager.get_batch_items(
        mock_db_manager, "test_batch_items"
    )
    assert len(result) == 2
    assert result[0]["paper_id"] == 1
    assert result[0]["batch_id"] == "test_batch_items"
    assert result[0]["status"] == "pending"
    assert "Summarize this paper" in result[0]["input_data"]
    assert result[1]["paper_id"] == 2


@pytest.mark.asyncio
async def test_add_batch_items_empty_list(
    batch_state_manager: BatchStateManager, mock_db_manager: DatabaseManager
) -> None:
    """Test adding empty list of batch items."""
    # Arrange - Create a batch record first
    await batch_state_manager.create_batch_record(
        mock_db_manager,
        batch_id="test_batch_empty",
        input_file_id="file_123",
    )

    # Act - Add empty list
    await batch_state_manager.add_batch_items(mock_db_manager, "test_batch_empty", [])

    # Assert - Verify no items were added
    result = await batch_state_manager.get_batch_items(
        mock_db_manager, "test_batch_empty"
    )
    assert len(result) == 0


@pytest.mark.asyncio
async def test_update_batch_item_status_success(
    batch_state_manager: BatchStateManager, mock_db_manager: DatabaseManager
) -> None:
    """Test successful update of batch item status."""
    # Arrange - Create a batch record and add items
    await batch_state_manager.create_batch_record(
        mock_db_manager,
        batch_id="test_batch_item_update",
        input_file_id="file_123",
    )

    # Create test papers
    await mock_db_manager.execute(
        """
        INSERT INTO paper (paper_id, arxiv_id, title, abstract, primary_category, categories, authors, url_abs, url_pdf, published_at, updated_at)
        VALUES (1, '2205.14135', 'Test Paper 1', 'This is a test abstract for paper 1', 'cs.AI', 'cs.AI,cs.LG', 'Author 1, Author 2', 'https://arxiv.org/abs/2205.14135', 'https://arxiv.org/pdf/2205.14135', '2022-05-28', '2022-05-28')
        """
    )

    # Add batch item
    items = [
        {
            "paper_id": 1,
            "input_data": '{"messages": [{"role": "user", "content": "Summarize this paper"}]}',
        },
    ]
    await batch_state_manager.add_batch_items(
        mock_db_manager, "test_batch_item_update", items
    )

    # Act - Update item status
    await batch_state_manager.update_batch_item_status(
        mock_db_manager,
        batch_id="test_batch_item_update",
        paper_id=1,
        status="completed",
        output_data='{"summary": "This is a test summary"}',
    )

    # Assert - Verify the status was updated
    result = await batch_state_manager.get_batch_items(
        mock_db_manager, "test_batch_item_update"
    )
    assert len(result) == 1
    assert result[0]["status"] == "completed"
    assert result[0]["output_data"] == '{"summary": "This is a test summary"}'
    assert result[0]["processed_at"] is not None  # Should be set for completed status


@pytest.mark.asyncio
async def test_update_batch_item_status_with_error(
    batch_state_manager: BatchStateManager, mock_db_manager: DatabaseManager
) -> None:
    """Test updating batch item status with error."""
    # Arrange - Create a batch record and add items
    await batch_state_manager.create_batch_record(
        mock_db_manager,
        batch_id="test_batch_item_error",
        input_file_id="file_123",
    )

    # Create test papers
    await mock_db_manager.execute(
        """
        INSERT INTO paper (paper_id, arxiv_id, title, abstract, primary_category, categories, authors, url_abs, url_pdf, published_at, updated_at)
        VALUES (2, '2205.14136', 'Test Paper 2', 'This is a test abstract for paper 2', 'cs.AI', 'cs.AI,cs.CL', 'Author 3, Author 4', 'https://arxiv.org/abs/2205.14136', 'https://arxiv.org/pdf/2205.14136', '2022-05-29', '2022-05-29')
        """
    )

    # Add batch item
    items = [
        {
            "paper_id": 2,
            "input_data": '{"messages": [{"role": "user", "content": "Summarize this paper"}]}',
        },
    ]
    await batch_state_manager.add_batch_items(
        mock_db_manager, "test_batch_item_error", items
    )

    # Act - Update item status to failed
    await batch_state_manager.update_batch_item_status(
        mock_db_manager,
        batch_id="test_batch_item_error",
        paper_id=2,
        status="failed",
        error_message="Processing failed due to invalid input",
    )

    # Assert - Verify the status was updated
    result = await batch_state_manager.get_batch_items(
        mock_db_manager, "test_batch_item_error"
    )
    assert len(result) == 1
    assert result[0]["status"] == "failed"
    assert result[0]["error_message"] == "Processing failed due to invalid input"
    assert result[0]["processed_at"] is not None  # Should be set for failed status


@pytest.mark.asyncio
async def test_get_active_batches_success(
    batch_state_manager: BatchStateManager, mock_db_manager: DatabaseManager
) -> None:
    """Test successful retrieval of active batches."""
    # Arrange - Insert test batch requests
    await mock_db_manager.execute(
        """
        INSERT INTO llm_batch_requests (batch_id, status, input_file_id, created_at)
        VALUES ('batch_123', 'in_progress', 'file_123', '2024-01-01T10:00:00Z'),
               ('batch_456', 'validating', 'file_456', '2024-01-01T11:00:00Z')
        """
    )

    # Act
    result = await batch_state_manager.get_active_batches(mock_db_manager)

    # Assert
    assert len(result) == 2
    # Check that both batches are returned (order may vary due to ORDER BY created_at DESC)
    batch_ids = {result[0]["batch_id"], result[1]["batch_id"]}
    statuses = {result[0]["status"], result[1]["status"]}
    assert batch_ids == {"batch_123", "batch_456"}
    assert statuses == {"in_progress", "validating"}


@pytest.mark.asyncio
async def test_get_active_batches_empty_result(
    batch_state_manager: BatchStateManager, mock_db_manager: DatabaseManager
) -> None:
    """Test when no active batches exist."""
    # Act
    result = await batch_state_manager.get_active_batches(mock_db_manager)

    # Assert
    assert result == []


@pytest.mark.asyncio
async def test_get_active_batches_database_error(
    batch_state_manager: BatchStateManager,
) -> None:
    """Test handling of database errors for active batches."""
    # Arrange
    mock_db = AsyncMock(spec=DatabaseManager)
    mock_db.fetch_all.side_effect = Exception("Database connection failed")

    # Act & Assert
    with pytest.raises(Exception, match="Database connection failed"):
        await batch_state_manager.get_active_batches(mock_db)

    mock_db.fetch_all.assert_called_once()
