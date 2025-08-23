"""Streaming response models for real-time updates."""

from pydantic import BaseModel

from core.models import PaperResponse


class StreamingStatusEvent(BaseModel):
    """Status update event for streaming responses."""

    type: str = "status"
    message: str


class StreamingCompleteEvent(BaseModel):
    """Completion event for streaming responses."""

    type: str = "complete"
    paper: PaperResponse | None = None


class StreamingErrorEvent(BaseModel):
    """Error event for streaming responses."""

    type: str = "error"
    message: str
