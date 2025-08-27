"""ArXiv-specific paper extractor."""

import re
from datetime import datetime
from urllib.parse import urljoin
from xml.etree import ElementTree

import httpx

from core.extractors.base import BaseExtractor
from core.extractors.exceptions import (
    ExtractionError,
    InvalidIdentifierError,
    NetworkError,
    ParsingError,
)
from core.log import get_logger
from core.models.domain.paper_extraction import PaperMetadata

logger = get_logger(__name__)


class ArxivExtractor(BaseExtractor):
    """ArXiv-specific paper extractor."""

    def __init__(
        self,
        api_base_url: str = "https://export.arxiv.org/api/query",
        abs_base_url: str = "https://arxiv.org/abs",
        pdf_base_url: str = "https://arxiv.org/pdf",
    ) -> None:
        """Initialize ArXiv extractor.

        Args:
            api_base_url: Base URL for arXiv API
            abs_base_url: Base URL for arXiv abstract pages
            pdf_base_url: Base URL for arXiv PDF pages
        """
        self.base_url = api_base_url
        self.abs_base_url = abs_base_url
        self.pdf_base_url = pdf_base_url
        self.namespace = {
            "atom": "http://www.w3.org/2005/Atom",
            "arxiv": "http://arxiv.org/schemas/atom",
        }

    def can_extract(self, url: str) -> bool:
        """Check if this extractor can handle the given URL.

        Args:
            url: URL to check

        Returns:
            True if this extractor can handle the URL
        """
        return "arxiv.org" in url

    def extract_identifier(self, url: str) -> str:
        """Extract arXiv identifier from URL.

        Args:
            url: URL to extract identifier from

        Returns:
            arXiv identifier (e.g., "1706.03762")

        Raises:
            InvalidIdentifierError: If URL format is invalid
        """
        # Direct arXiv ID
        if re.match(r"^\d{4}\.\d{4,5}$", url):
            return url

        # Abstract URL
        abs_match = re.search(r"arxiv\.org/abs/(\d{4}\.\d{4,5})", url)
        if abs_match:
            return abs_match.group(1)

        # PDF URL
        pdf_match = re.search(r"arxiv\.org/pdf/(\d{4}\.\d{4,5})", url)
        if pdf_match:
            return pdf_match.group(1)

        # Versioned URL
        version_match = re.search(r"arxiv\.org/abs/(\d{4}\.\d{4,5})v\d+", url)
        if version_match:
            return version_match.group(1)

        raise InvalidIdentifierError(f"Could not extract arXiv ID from: {url}")

    async def extract_metadata_async(self, url: str) -> PaperMetadata:
        """Extract paper metadata from arXiv URL asynchronously.

        Args:
            url: URL to extract metadata from

        Returns:
            Paper metadata

        Raises:
            ExtractionError: If extraction fails
        """
        try:
            identifier = self.extract_identifier(url)
            xml_response = await self._fetch_paper_xml(identifier)
            return self._parse_xml_to_metadata(xml_response, identifier)
        except (InvalidIdentifierError, NetworkError, ParsingError) as e:
            raise ExtractionError(f"Failed to extract metadata from {url}: {e}") from e

    async def _fetch_paper_xml(self, identifier: str) -> str:
        """Fetch paper XML from arXiv API.

        Args:
            identifier: arXiv identifier

        Returns:
            XML response as string

        Raises:
            NetworkError: If network request fails
        """
        params = {
            "id_list": identifier,
            "start": "0",
            "max_results": "1",
        }

        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                response = await client.get(self.base_url, params=params)
                response.raise_for_status()
                return response.text
        except httpx.RequestError as e:
            raise NetworkError(f"Network error fetching paper {identifier}: {e}") from e
        except httpx.HTTPStatusError as e:
            raise NetworkError(f"HTTP error fetching paper {identifier}: {e}") from e

    def _parse_xml_to_metadata(
        self, xml_content: str, identifier: str
    ) -> PaperMetadata:
        """Parse XML content and extract paper metadata.

        Args:
            xml_content: XML response from arXiv API
            identifier: arXiv identifier

        Returns:
            Paper metadata

        Raises:
            ParsingError: If parsing fails
        """
        if not xml_content or not xml_content.strip():
            raise ParsingError("Empty XML content provided")

        try:
            root = ElementTree.fromstring(xml_content)
        except ElementTree.ParseError as e:
            raise ParsingError(f"Failed to parse XML: {e}") from e

        entries = root.findall("atom:entry", self.namespace)
        if not entries:
            raise ParsingError("No papers found in XML response")

        entry = entries[0]
        return self._parse_entry_to_metadata(entry, identifier)

    def _parse_entry_to_metadata(
        self, entry: ElementTree.Element, identifier: str
    ) -> PaperMetadata:
        """Parse a single entry element into PaperMetadata.

        Args:
            entry: XML entry element
            identifier: arXiv identifier

        Returns:
            Paper metadata
        """
        # Extract basic metadata
        title = self._extract_text(entry, "atom:title")
        abstract = self._extract_text(entry, "atom:summary")

        # Extract authors
        authors = self._extract_authors(entry)

        # Extract categories
        categories = self._extract_categories(entry)

        # Extract dates
        published_date = self._extract_date(entry, "atom:published")
        updated_date = self._extract_date(entry, "atom:updated")

        # Extract URLs
        url_abs = urljoin(self.abs_base_url, f"abs/{identifier}")
        url_pdf = urljoin(self.pdf_base_url, f"pdf/{identifier}")

        return PaperMetadata(
            title=title,
            abstract=abstract,
            authors=authors,
            published_date=published_date,
            updated_date=updated_date,
            url_abs=url_abs,
            url_pdf=url_pdf,
            categories=categories,
            keywords=[],  # ArXiv doesn't provide keywords
            doi=None,  # ArXiv doesn't provide DOI
            journal=None,
            volume=None,
            pages=None,
            raw_metadata={"arxiv_id": identifier},
        )

    def _extract_text(self, entry: ElementTree.Element, tag: str) -> str:
        """Extract text content from XML element.

        Args:
            entry: XML entry element
            tag: Tag name with namespace

        Returns:
            Extracted text
        """
        element = entry.find(tag, self.namespace)
        if element is not None and element.text:
            return element.text.strip()
        return ""

    def _extract_authors(self, entry: ElementTree.Element) -> list[str]:
        """Extract authors from XML entry.

        Args:
            entry: XML entry element

        Returns:
            List of author names
        """
        authors = []
        for author in entry.findall("atom:author", self.namespace):
            name_elem = author.find("atom:name", self.namespace)
            if name_elem is not None and name_elem.text:
                authors.append(name_elem.text.strip())
        return authors

    def _extract_categories(self, entry: ElementTree.Element) -> list[str]:
        """Extract categories from XML entry.

        Args:
            entry: XML entry element

        Returns:
            List of categories
        """
        categories = []
        for category in entry.findall("arxiv:primary_category", self.namespace):
            term = category.get("term")
            if term:
                categories.append(term)

        for category in entry.findall("arxiv:category", self.namespace):
            term = category.get("term")
            if term and term not in categories:
                categories.append(term)

        return categories

    def _extract_date(self, entry: ElementTree.Element, tag: str) -> str:
        """Extract date from XML entry.

        Args:
            entry: XML entry element
            tag: Date tag name

        Returns:
            Date string in ISO format
        """
        date_elem = entry.find(tag, self.namespace)
        if date_elem is not None and date_elem.text:
            try:
                # Parse ISO 8601 date format
                dt = datetime.fromisoformat(date_elem.text.replace("Z", "+00:00"))
                return dt.isoformat()
            except ValueError:
                # Fallback to original text
                return date_elem.text.strip()
        return ""
