"""ArXiv XML parser for extracting paper metadata from API responses."""

import re
from datetime import datetime
from xml.etree import ElementTree

from core import get_logger
from crawler.database import Paper

from .constants import (
    ARXIV_ABS_BASE_URL,
    ARXIV_NAMESPACES,
    ARXIV_PDF_BASE_URL,
    DEFAULT_PRIMARY_CATEGORY,
    ERROR_EXTRACTING_ARXIV_ID,
    ERROR_FAILED_TO_PARSE_XML,
    ERROR_INVALID_DATE_FORMAT,
    ERROR_NO_PAPERS_FOUND,
    ISO8601_DATE_FORMAT,
    LOG_SUCCESSFULLY_PARSED,
)

logger = get_logger(__name__)


class ArxivParser:
    """Parser for arXiv XML responses."""

    def __init__(self) -> None:
        """Initialize the parser."""
        # Register the arXiv namespace
        self.namespace = ARXIV_NAMESPACES

    def parse_paper(self, xml_content: str) -> Paper | None:
        """Parse XML content and extract paper metadata.

        Args:
            xml_content: XML response from arXiv API

        Returns:
            Paper object with extracted metadata or None if parsing fails
        """
        if not xml_content or not xml_content.strip():
            logger.warning("Empty XML content provided")
            return None

        try:
            root = ElementTree.fromstring(xml_content)
        except ElementTree.ParseError as e:
            logger.error(ERROR_FAILED_TO_PARSE_XML.format(e))
            return None

        entries = root.findall("atom:entry", self.namespace)
        if not entries:
            logger.warning(ERROR_NO_PAPERS_FOUND)
            return None

        entry = entries[0]
        return self._parse_entry(entry)

    def _parse_entry(self, entry: ElementTree.Element) -> Paper:
        """Parse a single entry element into a Paper object.

        Args:
            entry: XML entry element

        Returns:
            Paper object with extracted metadata
        """
        # Extract basic metadata
        arxiv_id = self._extract_arxiv_id(entry)
        title = self._extract_text(entry, "atom:title")
        abstract = self._extract_text(entry, "atom:summary")

        # Extract authors
        authors = self._extract_authors(entry)

        # Extract categories
        categories = self._extract_categories(entry)
        primary_category = (
            categories.split(",")[0].strip() if categories else DEFAULT_PRIMARY_CATEGORY
        )

        # Extract dates
        published_at = self._extract_date(entry, "atom:published")
        updated_at = self._extract_date(entry, "atom:updated")

        # Extract URLs
        url_abs = f"{ARXIV_ABS_BASE_URL}/{arxiv_id}"
        url_pdf = f"{ARXIV_PDF_BASE_URL}/{arxiv_id}"

        # Create Paper object
        paper = Paper(
            arxiv_id=arxiv_id,
            title=title,
            abstract=abstract,
            primary_category=primary_category,
            categories=categories,
            authors=authors,
            url_abs=url_abs,
            url_pdf=url_pdf,
            published_at=published_at,
            updated_at=updated_at,
        )

        logger.info(LOG_SUCCESSFULLY_PARSED.format(arxiv_id, title))
        return paper

    def _extract_arxiv_id(self, entry: ElementTree.Element) -> str:
        """Extract arXiv ID from entry."""
        # Try to get from id element
        id_elem = entry.find("atom:id", self.namespace)
        if id_elem is not None and id_elem.text:
            # Extract ID from URL like
            # "http://arxiv.org/abs/1706.03762v7" or
            # "http://arxiv.org/abs/1706.03762"
            match = re.search(r"/(\d+\.\d+)(?:v\d+)?$", id_elem.text)
            if match:
                return match.group(1)

        # Fallback: try to get from arxiv:primary_category
        primary_cat = entry.find("arxiv:primary_category", self.namespace)
        if primary_cat is not None:
            term = primary_cat.get("term")
            if term:
                # Extract ID from term like "http://arxiv.org/abs/1706.03762"
                match = re.search(r"/(\d+\.\d+)(?:v\d+)?$", term)
                if match:
                    return match.group(1)

        raise ValueError(ERROR_EXTRACTING_ARXIV_ID)

    def _extract_text(self, entry: ElementTree.Element, xpath: str) -> str:
        """Extract text content from an element."""
        elem = entry.find(xpath, self.namespace)
        if elem is not None and elem.text:
            return elem.text.strip()
        return ""

    def _extract_authors(self, entry: ElementTree.Element) -> str:
        """Extract authors as semicolon-separated string."""
        authors = []
        for author in entry.findall("atom:author", self.namespace):
            name_elem = author.find("atom:name", self.namespace)
            if name_elem is not None and name_elem.text:
                authors.append(name_elem.text.strip())

        return ";".join(authors) if authors else ""

    def _extract_categories(self, entry: ElementTree.Element) -> str:
        """Extract categories as comma-separated string."""
        categories = []

        # Get primary category
        primary_cat = entry.find("arxiv:primary_category", self.namespace)
        if primary_cat is not None:
            term = primary_cat.get("term")
            if term:
                categories.append(term)

        # Get additional categories (using both namespaces)
        for category in entry.findall("category"):
            term = category.get("term")
            if term and term not in categories:
                categories.append(term)

        # Also check for atom:category elements
        for category in entry.findall("atom:category", self.namespace):
            term = category.get("term")
            if term and term not in categories:
                categories.append(term)

        # Also check for arxiv:category elements
        for category in entry.findall("arxiv:category", self.namespace):
            term = category.get("term")
            if term and term not in categories:
                categories.append(term)

        return ",".join(categories) if categories else ""

    def _extract_date(self, entry: ElementTree.Element, xpath: str) -> str:
        """Extract and format date."""
        elem = entry.find(xpath, self.namespace)
        if elem is not None and elem.text:
            try:
                # Parse ISO format date and return in our expected format
                dt = datetime.fromisoformat(elem.text.replace("Z", "+00:00"))
                return dt.strftime(ISO8601_DATE_FORMAT)
            except ValueError:
                logger.warning(ERROR_INVALID_DATE_FORMAT.format(elem.text))

        # Fallback to current time
        return datetime.now().strftime(ISO8601_DATE_FORMAT)

    def _extract_doi(self, entry: ElementTree.Element) -> str | None:
        """Extract DOI if available."""
        # Look for DOI in links
        for link in entry.findall("atom:link", self.namespace):
            href = link.get("href", "")
            if "doi.org" in href:
                return href

        # Look for DOI in arxiv:doi element
        doi_elem = entry.find("arxiv:doi", self.namespace)
        if doi_elem is not None and doi_elem.text:
            return doi_elem.text.strip()

        return None

    def _extract_comments(self, entry: ElementTree.Element) -> str | None:
        """Extract comments if available."""
        comments_elem = entry.find("arxiv:comment", self.namespace)
        if comments_elem is not None and comments_elem.text:
            return comments_elem.text.strip()
        return None
