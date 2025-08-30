"""Utility functions for the application."""

import json
from datetime import UTC, datetime
from typing import Any

from core import get_logger

logger = get_logger(__name__)


def get_current_timestamp() -> str:
    """Get current timestamp in ISO8601 format."""
    return datetime.now(UTC).isoformat()


def parse_iso_date(date_string: str | None) -> datetime | None:
    """Parse ISO date string to datetime object.

    Args:
        date_string: ISO format date string or None

    Returns:
        Parsed datetime object or None if parsing fails or input is None
    """
    if not date_string:
        return None

    try:
        return datetime.fromisoformat(date_string.replace("Z", "+00:00"))
    except ValueError:
        return None


def parse_datetime(date_str: str | None) -> datetime | None:
    """Parse datetime string to Python datetime object."""
    if not date_str:
        return None

    try:
        # Try parsing ISO format
        return datetime.fromisoformat(date_str.replace("Z", "+00:00"))
    except ValueError:
        pass

    try:
        # Try parsing other common formats
        return datetime.strptime(date_str, "%Y-%m-%dT%H:%M:%S%z")
    except ValueError:
        logger.warning(f"Could not parse date: {date_str}")
        return None


def parse_sse_events(content: str) -> list[dict[str, Any]]:
    """Parse Server-Sent Events content into list of events.

    Args:
        content: Raw SSE content string

    Returns:
        List of parsed event dictionaries
    """
    events = []
    for line in content.strip().split("\n"):
        if line.startswith("data: "):
            event_data = line[6:]  # Remove "data: " prefix
            if event_data.strip():
                try:
                    event = json.loads(event_data)
                    events.append(event)
                except json.JSONDecodeError:
                    continue
    return events
