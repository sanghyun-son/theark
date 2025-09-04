"""Tests for background batch manager daily limit functionality."""

import json
import pytest
from unittest.mock import Mock, patch
from sqlalchemy.engine import Engine

from core.batch.background_manager import BackgroundBatchManager
from core.database.repository import (
    LLMBatchRepository,
    PaperRepository,
    SummaryRepository,
)
from core.models.batch import BatchResult
from core.models.rows import Paper, Summary, LLMBatchRequest
from core.types import PaperSummaryStatus
from datetime import datetime, UTC
from sqlmodel import Session, select
from core.log import get_logger

logger = get_logger(__name__)


def create_mock_successful_result(paper_id: int) -> BatchResult:
    """Create a mock successful BatchResult with valid tool calls."""
    return BatchResult(
        custom_id=str(paper_id),
        status_code=200,
        response={
            "body": {
                "id": "chatcmpl-batch-tool-1",
                "object": "chat.completion",
                "created": 1677652288,
                "model": "gpt-4o-mini",
                "choices": [
                    {
                        "index": 0,
                        "message": {
                            "role": "assistant",
                            "content": None,
                            "tool_calls": [
                                {
                                    "id": "call_batch_tool_1",
                                    "type": "function",
                                    "function": {
                                        "name": "Structure",
                                        "arguments": '{"tldr": "Advanced machine learning approach for paper analysis.", "motivation": "Need for better understanding of research papers.", "method": "Novel neural network architecture with attention mechanisms.", "result": "Improved accuracy in paper summarization by 15%.", "conclusion": "The proposed method shows significant improvement over baseline.", "relevance": "9"}',
                                    },
                                }
                            ],
                        },
                        "finish_reason": "tool_calls",
                    }
                ],
                "usage": {
                    "prompt_tokens": 45,
                    "completion_tokens": 25,
                    "total_tokens": 70,
                },
            }
        },
        error=None,
    )


def create_mock_failed_result(paper_id: int) -> BatchResult:
    """Create a mock failed BatchResult."""
    return BatchResult(
        custom_id=str(paper_id),
        status_code=400,
        response={"body": {"error": {"message": "Invalid input format"}}},
        error=None,
    )


def create_mock_malformed_result(paper_id: int) -> BatchResult:
    """Create a mock result with malformed response (no tool calls)."""
    return BatchResult(
        custom_id=str(paper_id),
        status_code=200,
        response={
            "body": {
                "id": "chatcmpl-batch-tool-1",
                "object": "chat.completion",
                "created": 1677652288,
                "model": "gpt-4o-mini",
                "choices": [
                    {
                        "index": 0,
                        "message": {
                            "role": "assistant",
                            "content": "This is just text, no tool calls",
                            "tool_calls": None,  # No tool calls
                        },
                        "finish_reason": "stop",
                    }
                ],
                "usage": {
                    "prompt_tokens": 30,
                    "completion_tokens": 15,
                    "total_tokens": 45,
                },
            }
        },
        error=None,
    )


def create_mock_invalid_format_result(paper_id: int) -> BatchResult:
    """Create a mock result with invalid tool call format."""
    return BatchResult(
        custom_id=str(paper_id),
        status_code=200,
        response={
            "body": {
                "id": "chatcmpl-batch-tool-1",
                "object": "chat.completion",
                "created": 1677652288,
                "model": "gpt-4o-mini",
                "choices": [
                    {
                        "index": 0,
                        "message": {
                            "role": "assistant",
                            "content": None,
                            "tool_calls": [
                                {
                                    "id": "call_batch_tool_1",
                                    "type": "function",
                                    "function": {
                                        "name": "Structure",
                                        "arguments": '{"tldr": "Valid start", "motivation": "Valid motivation", "method": "Valid method", "result": "Valid result", "conclusion": "Valid conclusion", "relevance": "invalid_relevance"}',  # relevance should be int, not string
                                    },
                                }
                            ],
                        },
                        "finish_reason": "tool_calls",
                    }
                ],
                "usage": {
                    "prompt_tokens": 45,
                    "completion_tokens": 25,
                    "total_tokens": 70,
                },
            }
        },
        error=None,
    )


def create_mock_missing_fields_result(paper_id: int) -> BatchResult:
    """Create a mock result with missing required fields."""
    return BatchResult(
        custom_id=str(paper_id),
        status_code=200,
        response={
            "body": {
                "id": "chatcmpl-batch-tool-1",
                "object": "chat.completion",
                "created": 1677652288,
                "model": "gpt-4o-mini",
                "choices": [
                    {
                        "index": 0,
                        "message": {
                            "role": "assistant",
                            "content": None,
                            "tool_calls": [
                                {
                                    "id": "call_batch_tool_1",
                                    "type": "function",
                                    "function": {
                                        "name": "Structure",
                                        "arguments": '{"tldr": "Valid overview", "motivation": "Valid motivation"}',  # Missing method, result, conclusion, relevance
                                    },
                                }
                            ],
                        },
                        "finish_reason": "tool_calls",
                    }
                ],
                "usage": {
                    "prompt_tokens": 45,
                    "completion_tokens": 25,
                    "total_tokens": 70,
                },
            }
        },
        error=None,
    )


@pytest.mark.asyncio
async def test_check_daily_limit_under_limit(
    mock_db_engine: Engine,
    mock_background_manager: BackgroundBatchManager,
    llm_batch_repo: LLMBatchRepository,
) -> None:

    for i in range(3):
        llm_batch_repo.create_batch_record(
            batch_id=f"batch_{i}",
            input_file_id=f"file_{i}",
            completion_window="24h",
            endpoint="/v1/chat/completions",
            entity_count=1,
        )

    result: bool = await mock_background_manager._check_daily_limit(mock_db_engine)
    assert result is True


@pytest.mark.asyncio
async def test_check_daily_limit_exceeded(
    mock_db_engine: Engine,
    mock_background_manager: BackgroundBatchManager,
    llm_batch_repo: LLMBatchRepository,
) -> None:

    for i in range(6):
        llm_batch_repo.create_batch_record(
            batch_id=f"batch_{i}",
            input_file_id=f"file_{i}",
            completion_window="24h",
            endpoint="/v1/chat/completions",
            entity_count=5,
        )

    result: bool = await mock_background_manager._check_daily_limit(mock_db_engine)
    assert result is False

    @pytest.mark.asyncio
    async def test_process_single_result_success_returns_summary(
        mock_db_engine: Engine,
        mock_background_manager: BackgroundBatchManager,
        paper_repo: PaperRepository,
        saved_paper: Paper,
    ) -> None:
        """Test that successful batch result creates and returns Summary object."""

        # Create a mock successful BatchResult using helper function
        assert saved_paper.paper_id is not None, "Paper ID should not be None"
        mock_result = create_mock_successful_result(saved_paper.paper_id)

        # Process the result
        success, summary = await mock_background_manager._process_single_result(
            mock_db_engine, "test_batch", mock_result
        )

        # Verify that Summary was created and returned
        assert success is True, "Should return success=True"
        assert summary is not None, "Should return summary object"
        assert (
            summary.paper_id == saved_paper.paper_id
        ), "Summary should reference correct paper"
        assert summary.content is not None, "Summary should have content"

        # Verify summary content structure
        assert (
            summary.overview == "Advanced machine learning approach for paper analysis."
        )
        assert summary.motivation == "Need for better understanding of research papers."
        assert (
            summary.method
            == "Novel neural network architecture with attention mechanisms."
        )
        assert summary.result == "Improved accuracy in paper summarization by 15%."
        assert (
            summary.conclusion
            == "The proposed method shows significant improvement over baseline."
        )
        assert summary.relevance == 9
        assert summary.language == "English"  # From mock_background_manager fixture
        assert summary.model == "gpt-4o-mini"


@pytest.mark.asyncio
async def test_process_single_result_failure_logs_error(
    mock_db_engine: Engine,
    mock_background_manager: BackgroundBatchManager,
    paper_repo: PaperRepository,
    saved_paper: Paper,
) -> None:
    """Test that failed batch result logs error without saving summary."""

    # Create a mock failed BatchResult using helper function
    assert saved_paper.paper_id is not None, "Paper ID should not be None"
    mock_result = create_mock_failed_result(saved_paper.paper_id)

    # Process the result
    success, summary = await mock_background_manager._process_single_result(
        mock_db_engine, "test_batch", mock_result
    )

    # Verify that no Summary was returned for failed result
    assert success is False, "Should return success=False"
    assert summary is None, "Should return no summary for failed result"


@pytest.mark.asyncio
async def test_process_single_result_malformed_response_handling(
    mock_db_engine: Engine,
    mock_background_manager: BackgroundBatchManager,
    paper_repo: PaperRepository,
    saved_paper: Paper,
) -> None:
    """Test that malformed OpenAI response is handled gracefully."""

    # Create a mock result with malformed response using helper function
    assert saved_paper.paper_id is not None, "Paper ID should not be None"
    mock_result = create_mock_malformed_result(saved_paper.paper_id)

    # Process the result
    success, summary = await mock_background_manager._process_single_result(
        mock_db_engine, "test_batch", mock_result
    )

    # Verify that no Summary was returned for malformed response
    assert success is False, "Should return success=False"
    assert summary is None, "Should return no summary for malformed response"


@pytest.mark.asyncio
async def test_process_single_result_invalid_tool_call_format(
    mock_db_engine: Engine,
    mock_background_manager: BackgroundBatchManager,
    paper_repo: PaperRepository,
    saved_paper: Paper,
) -> None:
    """Test that invalid tool call format is handled gracefully."""

    # Create a mock result with invalid tool call format using helper function
    assert saved_paper.paper_id is not None, "Paper ID should not be None"
    mock_result = create_mock_invalid_format_result(saved_paper.paper_id)

    # Process the result
    success, summary = await mock_background_manager._process_single_result(
        mock_db_engine, "test_batch", mock_result
    )

    # Verify that no Summary was returned for invalid format
    assert success is False, "Should return success=False"
    assert summary is None, "Should return no summary for invalid format"


@pytest.mark.asyncio
async def test_process_single_result_missing_required_fields(
    mock_db_engine: Engine,
    mock_background_manager: BackgroundBatchManager,
    paper_repo: PaperRepository,
    saved_paper: Paper,
) -> None:
    """Test that missing required fields are handled gracefully."""

    # Create a mock result with missing required fields using helper function
    assert saved_paper.paper_id is not None, "Paper ID should not be None"
    mock_result = create_mock_missing_fields_result(saved_paper.paper_id)

    # Process the result
    success, summary = await mock_background_manager._process_single_result(
        mock_db_engine, "test_batch", mock_result
    )

    # Verify that no Summary was returned for missing fields
    assert success is False, "Should return success=False"
    assert summary is None, "Should return no summary for missing fields"


@pytest.mark.asyncio
async def test_process_batch_results_processes_all_results(
    mock_db_engine: Engine,
    mock_background_manager: BackgroundBatchManager,
    paper_repo: PaperRepository,
    saved_paper: Paper,
) -> None:
    """Test that _process_batch_results processes all results in a batch."""

    # Create multiple mock results
    assert saved_paper.paper_id is not None, "Paper ID should not be None"
    results = [
        create_mock_successful_result(saved_paper.paper_id),
        create_mock_failed_result(saved_paper.paper_id),
        create_mock_successful_result(saved_paper.paper_id),
    ]

    # Process the batch
    await mock_background_manager._process_batch_results_direct(
        mock_db_engine, "test_batch", results
    )

    # Verify that successful results created summaries

    with Session(mock_db_engine) as session:
        summary_repo = SummaryRepository(session)
        saved_summaries = await summary_repo.get_by_paper_id(saved_paper.paper_id)
        assert (
            len(saved_summaries) == 2
        ), "Should have 2 summaries from 2 successful results"


@pytest.mark.asyncio
async def test_process_batch_results_updates_paper_and_batch_status(
    mock_db_engine: Engine,
    mock_background_manager: BackgroundBatchManager,
    paper_repo: PaperRepository,
    saved_paper: Paper,
) -> None:
    """Test that paper and batch statuses are updated when processing completes."""

    # Create a batch request

    batch_request = LLMBatchRequest(
        batch_id="test_batch",
        entity_count=1,
        status="in_progress",
        created_at=datetime.now(UTC).isoformat(),
    )

    with Session(mock_db_engine) as session:
        batch_repo = LLMBatchRepository(session)
        session.add(batch_request)
        session.commit()

    # Process results
    assert saved_paper.paper_id is not None, "Paper ID should not be None"
    results = [create_mock_successful_result(saved_paper.paper_id)]
    await mock_background_manager._process_batch_results_direct(
        mock_db_engine, "test_batch", results
    )

    # Verify paper status updated to DONE
    updated_paper = paper_repo.get_by_id(saved_paper.paper_id)
    assert updated_paper is not None, "Paper should exist"
    assert updated_paper.summary_status == PaperSummaryStatus.DONE

    # Verify batch status updated to completed
    with Session(mock_db_engine) as session:
        batch_repo = LLMBatchRepository(session)
        # Use direct query since get_by_id expects int but batch_id is str
        statement = select(LLMBatchRequest).where(
            LLMBatchRequest.batch_id == "test_batch"
        )
        result = session.exec(statement)
        updated_batch = result.first()
        assert updated_batch is not None, "Batch should exist"
        assert updated_batch.status == "completed"


@pytest.mark.asyncio
async def test_process_batch_results_tracks_processing_metrics(
    mock_db_engine: Engine,
    mock_background_manager: BackgroundBatchManager,
    paper_repo: PaperRepository,
    saved_paper: Paper,
) -> None:
    """Test that batch processing tracks success/failure metrics."""

    # Create a batch request

    batch_request = LLMBatchRequest(
        batch_id="test_batch",
        entity_count=2,  # Expecting 2 results
        status="in_progress",
        created_at=datetime.now(UTC).isoformat(),
    )

    with Session(mock_db_engine) as session:
        session.add(batch_request)
        session.commit()

    # Process mixed results (1 success, 1 failure)
    assert saved_paper.paper_id is not None, "Paper ID should not be None"
    results = [
        create_mock_successful_result(saved_paper.paper_id),
        create_mock_failed_result(saved_paper.paper_id),
    ]

    # This should track that 1 succeeded and 1 failed
    await mock_background_manager._process_batch_results_direct(
        mock_db_engine, "test_batch", results
    )

    # Verify metrics are tracked (we'll implement this next)
    # For now, just verify the batch is marked as completed
    with Session(mock_db_engine) as session:
        statement = select(LLMBatchRequest).where(
            LLMBatchRequest.batch_id == "test_batch"
        )
        result = session.exec(statement)
        updated_batch = result.first()
        assert updated_batch is not None, "Batch should exist"
        assert updated_batch.status == "completed"


@pytest.mark.asyncio
async def test_process_batch_results_completes_even_with_partial_success(
    mock_db_engine: Engine,
    mock_background_manager: BackgroundBatchManager,
    paper_repo: PaperRepository,
    saved_paper: Paper,
) -> None:
    """Test that batch completes even with partial success (some papers failed)."""

    # Create a batch request expecting 3 papers
    batch_request = LLMBatchRequest(
        batch_id="test_batch",
        entity_count=3,  # Expecting 3 papers
        status="in_progress",
        created_at=datetime.now(UTC).isoformat(),
    )

    with Session(mock_db_engine) as session:
        session.add(batch_request)
        session.commit()

    # Process only 2 results (1 success, 1 failure) - missing 1 result
    assert saved_paper.paper_id is not None, "Paper ID should not be None"
    results = [
        create_mock_successful_result(saved_paper.paper_id),
        create_mock_failed_result(saved_paper.paper_id),
        # Missing 1 result - but batch should still complete
    ]

    # This should complete the batch even with partial results
    await mock_background_manager._process_batch_results_direct(
        mock_db_engine, "test_batch", results
    )

    # Verify batch is marked as completed (not in_progress)
    with Session(mock_db_engine) as session:
        statement = select(LLMBatchRequest).where(
            LLMBatchRequest.batch_id == "test_batch"
        )
        result = session.exec(statement)
        updated_batch = result.first()
        assert updated_batch is not None, "Batch should exist"
        assert (
            updated_batch.status == "completed"
        ), "Batch should be completed even with partial results"
        assert (
            updated_batch.completed_at is not None
        ), "Completion timestamp should be set"


@pytest.mark.asyncio
async def test_process_batch_results_handles_system_errors_gracefully(
    mock_db_engine: Engine,
    mock_background_manager: BackgroundBatchManager,
    paper_repo: PaperRepository,
    saved_paper: Paper,
) -> None:
    """Test that system-level errors are handled correctly and mark batch as error."""

    # Create a batch request
    batch_request = LLMBatchRequest(
        batch_id="test_batch",
        entity_count=1,
        status="in_progress",
        created_at=datetime.now(UTC).isoformat(),
    )

    with Session(mock_db_engine) as session:
        session.add(batch_request)
        session.commit()

    # Create a result that will cause a system-level error
    # We'll mock the _process_single_result to raise a system-level exception
    async def mock_process_single_result_with_error(*args, **kwargs):
        raise RuntimeError("Database connection failed")  # System-level error

    # Patch the method to simulate a system failure
    with patch.object(
        mock_background_manager,
        "_process_single_result",
        mock_process_single_result_with_error,
    ):
        results = [create_mock_successful_result(1)]

        # This should trigger system error handling and mark batch as "error"
        await mock_background_manager._process_batch_results_direct(
            mock_db_engine, "test_batch", results
        )

    # Verify batch is marked as error due to system-level failure
    with Session(mock_db_engine) as session:
        statement = select(LLMBatchRequest).where(
            LLMBatchRequest.batch_id == "test_batch"
        )
        result = session.exec(statement)
        updated_batch = result.first()
        assert updated_batch is not None, "Batch should exist"
        assert (
            updated_batch.status == "error"
        ), "Batch should be marked as error on system failure"


@pytest.mark.asyncio
async def test_process_batch_results_tracks_completion_metrics(
    mock_db_engine: Engine,
    mock_background_manager: BackgroundBatchManager,
    paper_repo: PaperRepository,
    saved_paper: Paper,
) -> None:
    """Test that batch processing tracks completion metrics (successful vs failed counts)."""

    # Create a batch request
    batch_request = LLMBatchRequest(
        batch_id="test_batch",
        entity_count=3,  # Expecting 3 papers
        status="in_progress",
        created_at=datetime.now(UTC).isoformat(),
    )

    with Session(mock_db_engine) as session:
        session.add(batch_request)
        session.commit()

    # Process mixed results (2 success, 1 failure)
    assert saved_paper.paper_id is not None, "Paper ID should not be None"
    results = [
        create_mock_successful_result(saved_paper.paper_id),
        create_mock_successful_result(saved_paper.paper_id),
        create_mock_failed_result(saved_paper.paper_id),
    ]

    # This should track metrics: 2 successful, 1 failed
    await mock_background_manager._process_batch_results_direct(
        mock_db_engine, "test_batch", results
    )

    # Verify batch is completed and has metrics
    with Session(mock_db_engine) as session:
        statement = select(LLMBatchRequest).where(
            LLMBatchRequest.batch_id == "test_batch"
        )
        result = session.exec(statement)
        updated_batch = result.first()
        assert updated_batch is not None, "Batch should exist"
        assert updated_batch.status == "completed"

        # Verify metrics are stored
        assert updated_batch.successful_count == 2, "Should have 2 successful results"
        assert updated_batch.failed_count == 1, "Should have 1 failed result"
        assert (
            updated_batch.completed_at is not None
        ), "Completion timestamp should be set"


@pytest.mark.asyncio
async def test_batch_processing_integration_flow(
    mock_db_engine: Engine,
    mock_background_manager: BackgroundBatchManager,
    paper_repo: PaperRepository,
    saved_paper: Paper,
) -> None:
    """Test the complete batch processing flow: Upload → Wait → Get Results."""

    # Mock OpenAI client responses for the entire flow
    mock_openai_client = Mock()

    # 1. MOCK UPLOAD PHASE
    # Mock file upload response (needs to be async)
    async def mock_upload_data(data: str, filename: str, purpose: str) -> str:
        return "file_123"

    mock_openai_client.upload_data = mock_upload_data

    # Mock batch creation response (needs to be async)
    async def mock_create_batch_request(
        input_file_id: str, completion_window: str, endpoint: str
    ):
        mock_batch_response = Mock()
        mock_batch_response.id = "batch_456"
        return mock_batch_response

    mock_openai_client.create_batch_request = mock_create_batch_request

    # 2. MOCK WAITING PHASE
    # Mock batch status response (needs to be async)
    async def mock_get_batch_status(batch_id: str):
        mock_batch_status = Mock()
        mock_batch_status.status = "completed"
        mock_batch_status.output_file_id = "output_789"
        mock_batch_status.error_file_id = None
        return mock_batch_status

    mock_openai_client.get_batch_status = mock_get_batch_status

    # 3. MOCK GET RESULTS PHASE
    # Mock file download response (JSONL format)
    mock_jsonl_content = json.dumps(
        {
            "custom_id": str(saved_paper.paper_id),
            "status_code": 200,
            "response": {
                "body": {
                    "id": "chatcmpl-batch-1",
                    "object": "chat.completion",
                    "created": 1677652288,
                    "model": "gpt-4o-mini",
                    "choices": [
                        {
                            "index": 0,
                            "message": {
                                "role": "assistant",
                                "content": None,
                                "tool_calls": [
                                    {
                                        "id": "call_1",
                                        "type": "function",
                                        "function": {
                                            "name": "Structure",
                                            "arguments": '{"tldr": "Test paper analysis.", "motivation": "Testing batch processing.", "method": "Integration testing approach.", "result": "Successful batch processing verification.", "conclusion": "Batch flow works correctly.", "relevance": "9"}',
                                        },
                                    }
                                ],
                            },
                            "finish_reason": "tool_calls",
                        }
                    ],
                    "usage": {
                        "prompt_tokens": 45,
                        "completion_tokens": 25,
                        "total_tokens": 70,
                    },
                }
            },
            "error": None,
        }
    )

    # Mock file download to return our JSONL content
    async def mock_download_file(file_id: str, file_path: str) -> None:
        with open(file_path, "w") as f:
            f.write(mock_jsonl_content)

    mock_openai_client.download_file = mock_download_file

    # Mock the summary service methods to return proper data structures
    mock_background_manager._summary_service._create_summarization_messages = Mock(
        return_value=[{"role": "user", "content": "Test prompt"}]
    )
    mock_background_manager._summary_service._create_paper_analysis_tool = Mock(
        return_value={
            "type": "function",
            "function": {
                "name": "Structure",
                "description": "Structure the paper analysis",
                "parameters": {
                    "type": "object",
                    "description": "Parameters for structuring paper analysis",
                    "properties": {
                        "tldr": {
                            "type": "string",
                            "description": "Brief summary of the paper",
                        },
                        "motivation": {
                            "type": "string",
                            "description": "Why this research was conducted",
                        },
                        "method": {
                            "type": "string",
                            "description": "Approach used in the research",
                        },
                        "result": {
                            "type": "string",
                            "description": "Key findings and outcomes",
                        },
                        "conclusion": {
                            "type": "string",
                            "description": "Main conclusions and implications",
                        },
                        "relevance": {
                            "type": "integer",
                            "description": "Relevance score from 1-10",
                        },
                    },
                    "required": [
                        "tldr",
                        "motivation",
                        "method",
                        "result",
                        "conclusion",
                        "relevance",
                    ],
                },
            },
        }
    )
    mock_background_manager._summary_service._create_tool_choice = Mock(
        return_value={"type": "function", "function": {"name": "Structure"}}
    )

    # Mock the OpenAI client model property
    mock_openai_client.model = "gpt-4o-mini"
    mock_openai_client.use_tools = True

    # 4. EXECUTE THE FLOW
    # Step 1: Create batch request (Upload phase)
    await mock_background_manager._create_batch_request(
        mock_db_engine, [saved_paper], mock_openai_client
    )

    # Verify batch was created in database
    with Session(mock_db_engine) as session:
        statement = select(LLMBatchRequest).where(
            LLMBatchRequest.batch_id == "batch_456"
        )
        result = session.exec(statement)
        created_batch = result.first()
        assert created_batch is not None, "Batch should be created"
        assert created_batch.input_file_id == "file_123"
        assert created_batch.entity_count == 1

    # Step 2: Process batch status (Wait phase)
    await mock_background_manager._process_batch_status(
        mock_db_engine, {"batch_id": "batch_456"}, mock_openai_client
    )

    # Step 3: Process batch results (Get Results phase)
    await mock_background_manager._process_batch_results(
        mock_db_engine, "batch_456", "output_789", mock_openai_client
    )

    # 5. VERIFY THE RESULTS
    # Check that summary was created and saved
    with Session(mock_db_engine) as session:
        summary_repo = SummaryRepository(session)
        assert saved_paper.paper_id is not None, "Paper ID should not be None"
        summaries = await summary_repo.get_by_paper_id(saved_paper.paper_id)
        assert len(summaries) > 0, "Summary should be created"

        # Verify summary content
        summary = summaries[0]
        assert summary.overview == "Test paper analysis."
        assert summary.motivation == "Testing batch processing."
        assert summary.method == "Integration testing approach."
        assert summary.result == "Successful batch processing verification."
        assert summary.conclusion == "Batch flow works correctly."
        assert summary.relevance == 9

    # Check that paper status was updated
    with Session(mock_db_engine) as session:
        paper_repo = PaperRepository(session)
        assert saved_paper.paper_id is not None, "Paper ID should not be None"
        updated_paper = paper_repo.get_by_id(saved_paper.paper_id)
        assert updated_paper is not None, "Paper should exist"
        assert updated_paper.summary_status == PaperSummaryStatus.DONE

    # Check that batch status was updated
    with Session(mock_db_engine) as session:
        statement = select(LLMBatchRequest).where(
            LLMBatchRequest.batch_id == "batch_456"
        )
        result = session.exec(statement)
        updated_batch = result.first()
        assert updated_batch is not None, "Batch should exist"
        assert updated_batch.status == "completed"
        assert updated_batch.completed_at is not None

    # Verify OpenAI client was called correctly
    # Note: Since we're using async functions, we can't use assert_called_once() directly
    # The calls were made during the flow execution
    logger.info("✅ Complete batch processing flow verified successfully!")

    logger.info("✅ Complete batch processing flow verified successfully!")
