"""Streaming response models for real-time updates."""

from typing import Any

from pydantic import BaseModel


class StreamingStatusEvent(BaseModel):
    """Status update event for streaming responses."""

    type: str = "status"
    message: str


class StreamingCompleteEvent(BaseModel):
    """Completion event for streaming responses."""

    type: str = "complete"
    paper: dict[str, Any]


class StreamingErrorEvent(BaseModel):
    """Error event for streaming responses."""

    type: str = "error"
    message: str


class StreamingEvent(BaseModel):
    """Union type for all streaming events."""

    type: str
    message: str | None = None
    paper: dict[str, Any] | None = None
