"""Utility functions for the application."""

import json
import xml.etree.ElementTree as ElementTree
from datetime import UTC, datetime, timedelta
from typing import Any

from core import get_logger

logger = get_logger(__name__)


def get_current_timestamp() -> str:
    """Get current timestamp in ISO8601 format."""
    return datetime.now(UTC).isoformat()


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

    # Get primary category (with arxiv: namespace)
    primary_elements = element.findall("arxiv:primary_category", namespace)
    for category_elem in primary_elements:
        category = category_elem.get("term")
        if category:
            categories.append(category)

    # Also get secondary categories (with atom: namespace)
    secondary_elements = element.findall("atom:category", namespace)

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


# Crawling utility functions
def parse_categories_string(categories_str: str) -> list[str]:
    """Parse comma-separated categories string into list.

    Args:
        categories_str: Comma-separated categories string

    Returns:
        List of category strings
    """
    if not categories_str:
        return []
    return [cat.strip() for cat in categories_str.split(",") if cat.strip()]


def format_date_range(start_date: str, end_date: str) -> str:
    """Format date range for logging.

    Args:
        start_date: Start date in YYYY-MM-DD format
        end_date: End date in YYYY-MM-DD format

    Returns:
        Formatted date range string
    """
    return f"Start date: {start_date}, End date: {end_date}"


def get_default_start_date() -> str:
    """Get default start date (yesterday).

    Returns:
        Yesterday's date in YYYY-MM-DD format
    """
    return (datetime.now() - timedelta(days=1)).strftime("%Y-%m-%d")


def is_date_before_end(current_date: str, end_date: str) -> bool:
    """Check if current date is before or equal to end date.

    Args:
        current_date: Current date in YYYY-MM-DD format
        end_date: End date in YYYY-MM-DD format

    Returns:
        True if current date is before or equal to end date
    """
    current = datetime.strptime(current_date, "%Y-%m-%d")
    end = datetime.strptime(end_date, "%Y-%m-%d")
    return current <= end


def get_previous_date(current_date: str) -> str:
    """Get previous date.

    Args:
        current_date: Current date in YYYY-MM-DD format

    Returns:
        Previous date in YYYY-MM-DD format
    """
    current = datetime.strptime(current_date, "%Y-%m-%d")
    previous = current - timedelta(days=1)
    return previous.strftime("%Y-%m-%d")


def is_date_before_start(current_date: str, start_date: str) -> bool:
    """Check if current date is before start date (exclusive).

    Args:
        current_date: Current date in YYYY-MM-DD format
        start_date: Start date in YYYY-MM-DD format

    Returns:
        True if current date is before start date
    """
    current = datetime.strptime(current_date, "%Y-%m-%d")
    start = datetime.strptime(start_date, "%Y-%m-%d")
    return current < start
