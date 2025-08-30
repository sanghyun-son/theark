"""Batch models for background processing."""

from datetime import datetime
from typing import Any

from pydantic import BaseModel, Field


class BatchItemCreate(BaseModel):
    """Model for creating batch items."""

    paper_id: int = Field(..., description="Paper identifier")
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


class PaperSummary(BaseModel):
    """Model for paper summary data."""

    paper_id: int = Field(..., description="Paper identifier")
    title: str = Field(..., description="Paper title")
    abstract: str = Field(..., description="Paper abstract")
    arxiv_id: str = Field(..., description="ArXiv ID")
    published_at: datetime | None = Field(None, description="Publication date")


# API Response Models
class BatchStatusResponse(BaseModel):
    """Model for batch status response."""

    pending_summaries: int = Field(..., description="Number of pending summaries")
    active_batches: int = Field(..., description="Number of active batches")
    batch_details: list[dict[str, Any]] = Field(..., description="Batch details")


class BatchListResponse(BaseModel):
    """Model for batch list response."""

    batches: list[dict[str, Any]] = Field(..., description="List of batches")


class BatchDetailsResponse(BaseModel):
    """Model for batch details response."""

    batch: dict[str, Any] = Field(..., description="Batch information")
    items: list[dict[str, Any]] = Field(..., description="Batch items")


class BatchItemsResponse(BaseModel):
    """Model for batch items response."""

    batch_id: str = Field(..., description="Batch ID")
    items: list[dict[str, Any]] = Field(..., description="Batch items")


class BatchActionResponse(BaseModel):
    """Model for batch action response."""

    message: str = Field(..., description="Action message")
    batch_id: str | None = Field(None, description="Batch ID")


class PendingSummariesResponse(BaseModel):
    """Model for pending summaries response."""

    pending_summaries: int = Field(..., description="Number of pending summaries")
    papers: list[dict[str, Any]] = Field(..., description="List of papers")
