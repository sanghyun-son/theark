"""Batch models for background processing."""

from typing import Any

from pydantic import BaseModel, Field

from core.models.rows import Summary


class BatchItemCreate(BaseModel):
    """Model for creating batch items."""

    paper_id: int | None = Field(..., description="Paper identifier")
    input_data: str = Field(..., description="Input data for processing")


class BatchRequestEntry(BaseModel):
    """Model for a single batch request entry."""

    custom_id: str = Field(..., description="Custom identifier")
    method: str = Field(..., description="HTTP method")
    url: str = Field(..., description="API endpoint URL")
    body: dict[str, Any] = Field(..., description="Request body")


class BatchRequestPayload(BaseModel):
    """Model for the complete batch request payload."""

    entries: list[BatchRequestEntry] = Field(..., description="List of request entries")

    def to_jsonl(self) -> str:
        """Convert to JSONL format for OpenAI Batch API."""
        return "\n".join(entry.model_dump_json() for entry in self.entries)


class BatchMetadata(BaseModel):
    """Model for batch metadata."""

    purpose: str = Field(..., description="Purpose of the batch")
    paper_count: int = Field(..., description="Number of papers in batch")
    model: str = Field(..., description="Model used for processing")


class BatchResult(BaseModel):
    """Model for a batch result."""

    custom_id: str = Field(..., description="Custom identifier")
    status_code: int = Field(..., description="HTTP status code")
    response: dict[str, Any] = Field(..., description="Response data")
    error: dict[str, Any] | None = Field(None, description="Error information")


# Core Batch Models
class BatchInfo(BaseModel):
    """Basic batch information."""

    batch_id: str = Field(..., description="Batch identifier")
    status: str = Field(..., description="Batch status")
    created_at: str = Field(..., description="Creation timestamp")
    completed_at: str | None = Field(None, description="Completion timestamp")
    entity_count: int = Field(..., description="Number of entities in batch")
    input_file_id: str | None = Field(None, description="Input file ID")
    error_file_id: str | None = Field(None, description="Error file ID")


# API Response Models
class BatchResponseBase(BaseModel):
    """Base class for batch API responses."""

    message: str | None = Field(None, description="Response message")


class BatchStatusResponse(BatchResponseBase):
    """Model for batch status response."""

    pending_summaries: int = Field(..., description="Number of pending summaries")
    active_batches: int = Field(..., description="Number of active batches")
    batch_details: list[BatchInfo] = Field(..., description="Batch details")


class BatchListResponse(BatchResponseBase):
    """Model for batch list response."""

    batches: list[BatchInfo] = Field(..., description="List of batches")


class BatchDetailsResponse(BatchResponseBase):
    """Model for batch details response."""

    batch: BatchInfo = Field(..., description="Batch information")
    message: str = Field(..., description="Response message")


class BatchActionResponse(BatchResponseBase):
    """Model for batch action response."""

    batch_id: str | None = Field(None, description="Batch ID")


class PendingSummariesResponse(BatchResponseBase):
    """Model for pending summaries response."""

    pending_summaries: int = Field(..., description="Number of pending summaries")
    papers: list[dict[str, Any]] = Field(..., description="List of papers")


# Bulk Processing Models
class BatchStatusInfo(BaseModel):
    """Batch status information from OpenAI API."""

    batch_id: str = Field(description="OpenAI batch ID")
    status: str = Field(description="Current batch status")
    output_file_id: str | None = Field(
        default=None, description="Output file ID if completed"
    )
    error_file_id: str | None = Field(
        default=None, description="Error file ID if failed"
    )
    created_at: str | None = Field(default=None, description="Creation timestamp")
    completed_at: str | None = Field(default=None, description="Completion timestamp")


class BatchProcessingResult(BaseModel):
    """Result of batch processing operation."""

    batch_info: BatchInfo = Field(description="Original batch information")
    status_info: BatchStatusInfo = Field(description="Status information from API")
    success: bool = Field(description="Whether processing was successful")
    error_message: str | None = Field(
        default=None, description="Error message if failed"
    )
    summaries: list[Summary] = Field(
        default_factory=list, description="Created summaries"
    )


class BulkProcessingSummary(BaseModel):
    """Summary of bulk processing operation."""

    total_batches: int = Field(description="Total number of batches processed")
    successful_batches: int = Field(
        description="Number of successfully processed batches"
    )
    failed_batches: int = Field(description="Number of failed batches")
    total_summaries: int = Field(description="Total number of summaries created")
    processing_time_seconds: float = Field(
        description="Total processing time in seconds"
    )
    batches_processed: list[BatchProcessingResult] = Field(
        description="Individual batch results"
    )
