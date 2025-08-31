"""Utility functions for the application."""

import json
import xml.etree.ElementTree as ElementTree
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


def extract_xml_text(
    element: ElementTree.Element, tag: str, namespace: dict[str, str] | None = None
) -> str:
    """Extract text content from XML element.

    Args:
        element: XML element
        tag: Tag name with namespace
        namespace: XML namespace dictionary

    Returns:
        Extracted text or empty string if not found
    """
    found_element = element.find(tag, namespace)
    if found_element is not None and found_element.text:
        return found_element.text.strip()
    return ""


def extract_xml_authors(
    element: ElementTree.Element, namespace: dict[str, str] | None = None
) -> list[str]:
    """Extract authors from XML element.

    Args:
        element: XML element
        namespace: XML namespace dictionary

    Returns:
        List of author names
    """
    authors = []
    author_elements = element.findall("atom:author/atom:name", namespace)

    for author_elem in author_elements:
        if author_elem.text:
            authors.append(author_elem.text.strip())

    return authors


def extract_xml_categories(
    element: ElementTree.Element, namespace: dict[str, str] | None = None
) -> list[str]:
    """Extract categories from XML element.

    Args:
        element: XML element
        namespace: XML namespace dictionary

    Returns:
        List of categories
    """
    categories = []
    category_elements = element.findall("arxiv:primary_category", namespace)

    for category_elem in category_elements:
        category = category_elem.get("term")
        if category:
            categories.append(category)

    # Also get secondary categories
    secondary_elements = element.findall("arxiv:category", namespace)
    for category_elem in secondary_elements:
        category = category_elem.get("term")
        if category and category not in categories:
            categories.append(category)

    return categories


def extract_xml_date(
    element: ElementTree.Element, tag: str, namespace: dict[str, str] | None = None
) -> str:
    """Extract date from XML element.

    Args:
        element: XML element
        tag: Tag name with namespace
        namespace: XML namespace dictionary

    Returns:
        Date string in ISO format or empty string if not found
    """
    date_text = extract_xml_text(element, tag, namespace)
    if date_text:
        try:
            # Parse and return in ISO format
            parsed_date = datetime.fromisoformat(date_text.replace("Z", "+00:00"))
            return parsed_date.isoformat()
        except ValueError:
            logger.warning(f"Could not parse date: {date_text}")
            return ""
    return ""
