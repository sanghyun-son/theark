"""Tests for streaming models."""

import pytest
from pydantic import ValidationError

from api.models.streaming import (
    StreamingStatusEvent,
    StreamingCompleteEvent,
    StreamingErrorEvent,
    StreamingEvent,
)


class TestStreamingStatusEvent:
    """Test StreamingStatusEvent model."""

    def test_valid_status_event(self):
        """Test creating valid status event."""
        event = StreamingStatusEvent(message="Test message")
        assert event.type == "status"
        assert event.message == "Test message"

    def test_status_event_default_type(self):
        """Test that type defaults to 'status'."""
        event = StreamingStatusEvent(message="Test message")
        assert event.type == "status"

    def test_status_event_missing_message(self):
        """Test that message is required."""
        with pytest.raises(ValidationError):
            StreamingStatusEvent()


class TestStreamingCompleteEvent:
    """Test StreamingCompleteEvent model."""

    def test_valid_complete_event(self):
        """Test creating valid complete event."""
        paper_data = {"paper_id": 1, "title": "Test Paper"}
        event = StreamingCompleteEvent(paper=paper_data)
        assert event.type == "complete"
        assert event.paper == paper_data

    def test_complete_event_default_type(self):
        """Test that type defaults to 'complete'."""
        event = StreamingCompleteEvent(paper={"test": "data"})
        assert event.type == "complete"

    def test_complete_event_missing_paper(self):
        """Test that paper is required."""
        with pytest.raises(ValidationError):
            StreamingCompleteEvent()


class TestStreamingErrorEvent:
    """Test StreamingErrorEvent model."""

    def test_valid_error_event(self):
        """Test creating valid error event."""
        event = StreamingErrorEvent(message="Error occurred")
        assert event.type == "error"
        assert event.message == "Error occurred"

    def test_error_event_default_type(self):
        """Test that type defaults to 'error'."""
        event = StreamingErrorEvent(message="Error occurred")
        assert event.type == "error"

    def test_error_event_missing_message(self):
        """Test that message is required."""
        with pytest.raises(ValidationError):
            StreamingErrorEvent()


class TestStreamingEvent:
    """Test StreamingEvent model."""

    def test_valid_streaming_event(self):
        """Test creating valid streaming event."""
        event = StreamingEvent(type="custom", message="Custom message")
        assert event.type == "custom"
        assert event.message == "Custom message"
        assert event.paper is None

    def test_streaming_event_with_paper(self):
        """Test creating streaming event with paper data."""
        paper_data = {"paper_id": 1, "title": "Test Paper"}
        event = StreamingEvent(type="custom", paper=paper_data)
        assert event.type == "custom"
        assert event.message is None
        assert event.paper == paper_data

    def test_streaming_event_missing_type(self):
        """Test that type is required."""
        with pytest.raises(ValidationError):
            StreamingEvent()

    def test_streaming_event_model_dump(self):
        """Test model serialization."""
        event = StreamingEvent(type="test", message="test message")
        data = event.model_dump()
        assert data["type"] == "test"
        assert data["message"] == "test message"
        assert data["paper"] is None
