"""Tests for OpenAI API models."""

import pytest
from pydantic import ValidationError

from core.models.external.openai import BatchRequest, BatchResponse


@pytest.fixture
def sample_batch_request_data() -> dict:
    """Sample data for BatchRequest."""
    return {
        "input_file_id": "file-abc123",
        "endpoint": "/v1/chat/completions",
        "completion_window": "24h",
        "metadata": {"custom_id": "test-batch-001"},
    }


@pytest.fixture
def sample_batch_response_data() -> dict:
    """Sample data for BatchResponse."""
    return {
        "id": "batch-xyz789",
        "object": "batch",
        "endpoint": "/v1/chat/completions",
        "input_file_id": "file-abc123",
        "completion_window": "24h",
        "status": "in_progress",
        "created_at": 1640995200,
        "in_progress_at": 1640995260,
        "expires_at": 1641081600,
        "request_counts": {"total": 100, "completed": 50, "failed": 0},
    }


def test_batch_request_creation(sample_batch_request_data: dict) -> None:
    """Test BatchRequest creation with valid data."""
    batch_request = BatchRequest(**sample_batch_request_data)

    assert batch_request.input_file_id == "file-abc123"
    assert batch_request.endpoint == "/v1/chat/completions"
    assert batch_request.completion_window == "24h"
    assert batch_request.metadata == {"custom_id": "test-batch-001"}


def test_batch_request_defaults() -> None:
    """Test BatchRequest creation with default values."""
    batch_request = BatchRequest(input_file_id="file-abc123")

    assert batch_request.input_file_id == "file-abc123"
    assert batch_request.endpoint == "/v1/chat/completions"
    assert batch_request.completion_window == "24h"
    assert batch_request.metadata is None


def test_batch_request_missing_required_field() -> None:
    """Test BatchRequest validation with missing required field."""
    with pytest.raises(ValidationError) as exc_info:
        BatchRequest(endpoint="/v1/chat/completions")

    assert "input_file_id" in str(exc_info.value)


def test_batch_request_with_metadata() -> None:
    """Test BatchRequest with metadata."""
    metadata = {
        "custom_id": "test-batch-001",
        "priority": "high",
        "tags": ["summarization", "papers"],
    }

    batch_request = BatchRequest(input_file_id="file-abc123", metadata=metadata)

    assert batch_request.metadata == metadata


def test_batch_response_creation(sample_batch_response_data: dict) -> None:
    """Test BatchResponse creation with valid data."""
    batch_response = BatchResponse(**sample_batch_response_data)

    assert batch_response.id == "batch-xyz789"
    assert batch_response.object == "batch"
    assert batch_response.endpoint == "/v1/chat/completions"
    assert batch_response.status == "in_progress"
    assert batch_response.created_at == 1640995200
    assert batch_response.request_counts == {"total": 100, "completed": 50, "failed": 0}


def test_batch_response_with_optional_fields() -> None:
    """Test BatchResponse with optional fields."""
    data = {
        "id": "batch-xyz789",
        "endpoint": "/v1/chat/completions",
        "input_file_id": "file-abc123",
        "completion_window": "24h",
        "status": "completed",
        "created_at": 1640995200,
        "output_file_id": "file-output-123",
        "error_file_id": "file-error-456",
        "completed_at": 1640996000,
        "metadata": {"custom_id": "test-batch-001"},
    }

    batch_response = BatchResponse(**data)

    assert batch_response.output_file_id == "file-output-123"
    assert batch_response.error_file_id == "file-error-456"
    assert batch_response.completed_at == 1640996000
    assert batch_response.metadata == {"custom_id": "test-batch-001"}


def test_batch_response_missing_required_fields() -> None:
    """Test BatchResponse validation with missing required fields."""
    with pytest.raises(ValidationError) as exc_info:
        BatchResponse(endpoint="/v1/chat/completions")

    error_str = str(exc_info.value)
    assert "id" in error_str
    assert "input_file_id" in error_str
    assert "completion_window" in error_str
    assert "status" in error_str
    assert "created_at" in error_str


def test_batch_response_status_values() -> None:
    """Test BatchResponse with different status values."""
    valid_statuses = ["validating", "failed", "in_progress", "completed", "expired"]

    for status in valid_statuses:
        data = {
            "id": "batch-xyz789",
            "endpoint": "/v1/chat/completions",
            "input_file_id": "file-abc123",
            "completion_window": "24h",
            "status": status,
            "created_at": 1640995200,
        }

        batch_response = BatchResponse(**data)
        assert batch_response.status == status


def test_batch_response_with_errors() -> None:
    """Test BatchResponse with error information."""
    errors = {"code": "invalid_file", "message": "Input file format is not supported"}

    data = {
        "id": "batch-xyz789",
        "endpoint": "/v1/chat/completions",
        "input_file_id": "file-abc123",
        "completion_window": "24h",
        "status": "failed",
        "created_at": 1640995200,
        "errors": errors,
    }

    batch_response = BatchResponse(**data)
    assert batch_response.errors == errors
    assert batch_response.status == "failed"


def test_batch_response_request_counts() -> None:
    """Test BatchResponse with request counts."""
    request_counts = {"total": 1000, "completed": 950, "failed": 25, "pending": 25}

    data = {
        "id": "batch-xyz789",
        "endpoint": "/v1/chat/completions",
        "input_file_id": "file-abc123",
        "completion_window": "24h",
        "status": "in_progress",
        "created_at": 1640995200,
        "request_counts": request_counts,
    }

    batch_response = BatchResponse(**data)
    assert batch_response.request_counts == request_counts


def test_batch_response_timestamps() -> None:
    """Test BatchResponse with various timestamp fields."""
    data = {
        "id": "batch-xyz789",
        "endpoint": "/v1/chat/completions",
        "input_file_id": "file-abc123",
        "completion_window": "24h",
        "status": "completed",
        "created_at": 1640995200,
        "in_progress_at": 1640995260,
        "expires_at": 1641081600,
        "finalizing_at": 1640995900,
        "completed_at": 1640996000,
    }

    batch_response = BatchResponse(**data)

    assert batch_response.created_at == 1640995200
    assert batch_response.in_progress_at == 1640995260
    assert batch_response.expires_at == 1641081600
    assert batch_response.finalizing_at == 1640995900
    assert batch_response.completed_at == 1640996000
