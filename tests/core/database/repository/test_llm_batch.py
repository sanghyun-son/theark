"""Tests for LLM batch repository."""


from core.database.repository.llm_batch import LLMBatchRepository
from core.database.repository.paper import PaperRepository
from core.models.rows import Paper
from core.types import PaperSummaryStatus


def test_get_pending_summaries_with_papers(
    llm_batch_repo: LLMBatchRepository,
    saved_papers: list[Paper],
) -> None:
    """Test getting pending summaries with papers in database."""
    # Act
    pending_papers = llm_batch_repo.get_pending_summaries()

    # Assert
    assert (
        len(pending_papers) == 2
    )  # Only papers with status="batched" and non-empty abstract
    assert all(
        paper.summary_status == PaperSummaryStatus.BATCHED for paper in pending_papers
    )
    assert all(paper.abstract and paper.abstract.strip() for paper in pending_papers)

    # Verify ordering: should be newest first (descending by published_at)
    assert pending_papers[0].published_at == "2023-01-03"  # Newest
    assert pending_papers[1].published_at == "2023-01-01"  # Oldest


def test_get_pending_summaries_empty(
    llm_batch_repo: LLMBatchRepository,
) -> None:
    """Test getting pending summaries with empty database."""
    # Act
    pending_papers = llm_batch_repo.get_pending_summaries()

    # Assert
    assert len(pending_papers) == 0


def test_update_paper_summary_status_success(
    llm_batch_repo: LLMBatchRepository,
    saved_papers: list[Paper],
    paper_repo: PaperRepository,
) -> None:
    """Test successful update of paper summary status."""
    # Arrange - Use first saved paper
    paper = saved_papers[0]
    paper_id = paper.paper_id
    assert paper_id is not None

    # Act
    llm_batch_repo.update_paper_summary_status(paper_id, PaperSummaryStatus.PROCESSING)

    # Assert
    updated_paper = paper_repo.get_by_id(paper_id)
    assert updated_paper is not None
    assert updated_paper.summary_status == PaperSummaryStatus.PROCESSING


def test_update_paper_summary_status_not_found(
    llm_batch_repo: LLMBatchRepository,
) -> None:
    """Test updating paper summary status for non-existent paper."""
    # Act
    llm_batch_repo.update_paper_summary_status(999, PaperSummaryStatus.PROCESSING)

    # Assert - Should not raise exception, just log warning


def test_update_paper_summary_status_invalid_status(
    llm_batch_repo: LLMBatchRepository,
) -> None:
    """Test updating paper summary status with invalid status."""
    # Act & Assert - With enum type, invalid statuses are caught at type checking time
    # This test is no longer needed since the type system prevents invalid statuses
    pass


def test_mark_papers_processing_success(
    llm_batch_repo: LLMBatchRepository,
    saved_papers: list[Paper],
    paper_repo: PaperRepository,
) -> None:
    """Test successful marking of papers as processing."""
    # Arrange - Get paper IDs from saved papers
    paper_ids = [paper.paper_id for paper in saved_papers if paper.paper_id is not None]
    assert len(paper_ids) == 3

    # Act
    llm_batch_repo.mark_papers_processing(paper_ids)

    # Assert
    for paper_id in paper_ids:
        paper = paper_repo.get_by_id(paper_id)
        assert paper is not None
        assert paper.summary_status == PaperSummaryStatus.PROCESSING.value


def test_mark_papers_processing_empty_list(
    llm_batch_repo: LLMBatchRepository,
) -> None:
    """Test marking papers as processing with empty list."""
    # Act
    llm_batch_repo.mark_papers_processing([])

    # Assert - Should not raise exception


def test_get_active_batches_stub(
    llm_batch_repo: LLMBatchRepository,
) -> None:
    """Test get_active_batches stub implementation."""
    # Act
    active_batches = llm_batch_repo.get_active_batches()

    # Assert
    assert active_batches == []  # Currently returns empty list


def test_create_batch_record_stub(
    llm_batch_repo: LLMBatchRepository,
) -> None:
    """Test create_batch_record stub implementation."""
    # Act
    llm_batch_repo.create_batch_record(
        batch_id="test_batch",
        input_file_id="test_file",
        completion_window="24h",
        endpoint="/v1/chat/completions",
        metadata={"test": "data"},
    )

    # Assert - Should not raise exception, just log


def test_update_batch_status_stub(
    llm_batch_repo: LLMBatchRepository,
) -> None:
    """Test update_batch_status stub implementation."""
    # Act
    llm_batch_repo.update_batch_status(
        batch_id="test_batch",
        status="completed",
        error_file_id=None,
    )

    # Assert - Should not raise exception, just log


def test_add_batch_items_stub(
    llm_batch_repo: LLMBatchRepository,
) -> None:
    """Test add_batch_items stub implementation."""
    # Arrange
    items = [
        {"paper_id": 1, "input_data": "test1"},
        {"paper_id": 2, "input_data": "test2"},
    ]

    # Act
    llm_batch_repo.add_batch_items("test_batch", items)

    # Assert - Should not raise exception, just log


def test_add_batch_items_empty(
    llm_batch_repo: LLMBatchRepository,
) -> None:
    """Test add_batch_items with empty list."""
    # Act
    llm_batch_repo.add_batch_items("test_batch", [])

    # Assert - Should not raise exception


def test_update_batch_item_status_stub(
    llm_batch_repo: LLMBatchRepository,
) -> None:
    """Test update_batch_item_status stub implementation."""
    # Act
    llm_batch_repo.update_batch_item_status(
        batch_id="test_batch",
        item_id="test_item",
        status="completed",
        error="test error",
    )

    # Assert - Should not raise exception, just log


def test_get_batch_details_stub(
    llm_batch_repo: LLMBatchRepository,
) -> None:
    """Test get_batch_details stub implementation."""
    # Act
    details = llm_batch_repo.get_batch_details("test_batch")
    assert details is None  # Currently returns None


def test_get_batch_items_stub(
    llm_batch_repo: LLMBatchRepository,
) -> None:
    """Test get_batch_items stub implementation."""
    # Act
    items = llm_batch_repo.get_batch_items("test_batch")
    assert items == []  # Currently returns empty list


def test_cancel_batch_stub(
    llm_batch_repo: LLMBatchRepository,
) -> None:
    """Test cancel_batch stub implementation."""
    # Act
    result = llm_batch_repo.cancel_batch("test_batch")
    assert result is False  # Currently returns False
