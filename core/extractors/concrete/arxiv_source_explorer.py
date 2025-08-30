"""ArXiv source explorer for bulk paper discovery."""

import asyncio
from datetime import datetime, timedelta
from typing import Any
from urllib.parse import urlencode

import httpx

from core.extractors.base import BaseSourceExplorer
from core.extractors.exceptions import NetworkError, ParsingError
from core.log import get_logger
from core.models.domain.arxiv import ArxivPaper
from core.models.domain.paper_extraction import PaperMetadata

from .arxiv_extractor import ArxivExtractor

logger = get_logger(__name__)


class ArxivSourceExplorer(BaseSourceExplorer):
    """ArXiv source explorer for bulk paper discovery."""

    def __init__(
        self,
        api_base_url: str = "https://export.arxiv.org/api/query",
        delay_seconds: float = 2.0,
        max_results_per_request: int = 100,
    ) -> None:
        """Initialize ArXiv source explorer.

        Args:
            api_base_url: Base URL for arXiv API
            delay_seconds: Delay between requests in seconds
            max_results_per_request: Maximum results per API request
        """
        self.api_base_url = api_base_url
        self.delay_seconds = delay_seconds
        self.max_results_per_request = max_results_per_request
        # Reuse ArxivExtractor for parsing
        self.extractor = ArxivExtractor(api_base_url=api_base_url)

    async def explore_recent(
        self,
        limit: int = 100,
        days_back: int = 7,
    ) -> list[PaperMetadata]:
        """Explore recent papers from ArXiv.

        Args:
            limit: Maximum number of papers to return
            days_back: Number of days back to consider "recent" (default: 30 days)

        Returns:
            List of recent paper metadata
        """
        # Calculate the start date based on days_back

        start_date = (datetime.now() - timedelta(days=days_back)).strftime("%Y-%m-%d")
        query = f"submittedDate:[{start_date}+TO+now]"
        return await self._explore_with_query(query, limit)

    async def explore_by_category(
        self, category: str, limit: int = 100
    ) -> list[PaperMetadata]:
        """Explore papers by category.

        Args:
            category: Category to explore (e.g., "cs.AI")
            limit: Maximum number of papers to return

        Returns:
            List of paper metadata in the category
        """
        query = f"cat:{category}"
        return await self._explore_with_query(query, limit)

    async def explore_new_papers_by_category(
        self, category: str, start_date: str, start_index: int = 0, limit: int = 100
    ) -> list[ArxivPaper]:
        """Explore new papers for a specific category from a given date.

        Args:
            category: ArXiv category (e.g., "cs.AI")
            start_date: Start date in YYYY-MM-DD format
            start_index: Starting index for pagination
            limit: Maximum number of papers to return

        Returns:
            List of ArXiv papers
        """
        query = f"submittedDate:[{start_date}+TO+now]+AND+cat:{category}"
        result = await self._explore_papers_with_query(query, start_index, limit)
        return result

    async def explore_historical_papers_by_category(
        self, category: str, date: str, start_index: int = 0, limit: int = 100
    ) -> list[ArxivPaper]:
        """Explore historical papers for a specific category on a specific date.

        Args:
            category: ArXiv category (e.g., "cs.AI")
            date: Date in YYYY-MM-DD format
            start_index: Starting index for pagination
            limit: Maximum number of papers to return

        Returns:
            List of ArXiv papers
        """
        query = f"submittedDate:[{date}+TO+{date}]+AND+cat:{category}"
        return await self._explore_papers_with_query(query, start_index, limit)

    async def explore_new_papers_by_category_as_arxiv(
        self, category: str, start_date: str, start_index: int = 0, limit: int = 100
    ) -> list[ArxivPaper]:
        """Explore new papers for a specific category from a given date (returns ArxivPaper).

        Args:
            category: ArXiv category (e.g., "cs.AI")
            start_date: Start date in YYYY-MM-DD format
            start_index: Starting index for pagination
            limit: Maximum number of papers to return

        Returns:
            List of ArXiv papers
        """
        result = await self.explore_new_papers_by_category(
            category, start_date, start_index, limit
        )
        return result

    async def explore_historical_papers_by_category_as_arxiv(
        self, category: str, date: str, start_index: int = 0, limit: int = 100
    ) -> list[ArxivPaper]:
        """Explore historical papers for a specific category on a specific date (returns ArxivPaper).

        Args:
            category: ArXiv category (e.g., "cs.AI")
            date: Date in YYYY-MM-DD format
            start_index: Starting index for pagination
            limit: Maximum number of papers to return

        Returns:
            List of ArXiv papers
        """
        result = await self.explore_historical_papers_by_category(
            category, date, start_index, limit
        )
        return result

    async def _explore_with_query(self, query: str, limit: int) -> list[PaperMetadata]:
        """Explore papers with a specific query.

        Args:
            query: ArXiv query string
            limit: Maximum number of papers to return

        Returns:
            List of paper metadata
        """
        papers: list[PaperMetadata] = []
        start_index = 0

        while len(papers) < limit:
            batch_size = min(self.max_results_per_request, limit - len(papers))

            try:
                batch = await self._fetch_papers_batch(query, start_index, batch_size)
                if not batch:
                    break

                # Convert ArxivPaper to PaperMetadata (they're compatible since ArxivPaper inherits from PaperMetadata)
                papers.extend(batch)
                start_index += len(batch)

                # Rate limiting
                await asyncio.sleep(self.delay_seconds)

            except (NetworkError, ParsingError) as e:
                logger.error(f"Error fetching papers batch: {e}")
                break

        return papers[:limit]

    async def _explore_papers_with_query(
        self, query: str, start_index: int, limit: int
    ) -> list[ArxivPaper]:
        """Explore ArXiv papers with a specific query.

        Args:
            query: ArXiv query string
            start_index: Starting index for pagination
            limit: Maximum number of papers to return

        Returns:
            List of ArXiv papers
        """
        try:
            batch = await self._fetch_papers_batch(query, start_index, limit)
            return batch
        except (NetworkError, ParsingError) as e:
            logger.error(f"Error fetching papers: {e}")
            return []

    async def _fetch_papers_batch(
        self, query: str, start: int, max_results: int
    ) -> list[ArxivPaper]:
        """Fetch a batch of papers from ArXiv API.

        Args:
            query: ArXiv query string
            start: Starting index
            max_results: Maximum number of results

        Returns:
            List of ArXiv papers

        Raises:
            NetworkError: If network request fails
            ParsingError: If response parsing fails
        """
        params = {
            "search_query": query,
            "start": str(start),
            "max_results": str(max_results),
            "sortBy": "submittedDate",
            "sortOrder": "descending",
        }

        url = f"{self.api_base_url}?{urlencode(params)}"

        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                response = await client.get(url)
                response.raise_for_status()
                return self._parse_xml_response(response.text)
        except httpx.RequestError as e:
            raise NetworkError(f"Network error fetching papers: {e}") from e
        except httpx.HTTPStatusError as e:
            raise NetworkError(f"HTTP error fetching papers: {e}") from e

    def _parse_xml_response(self, xml_content: str) -> list[ArxivPaper]:
        """Parse XML response from ArXiv API.

        Args:
            xml_content: XML response content

        Returns:
            List of ArXiv papers

        Raises:
            ParsingError: If parsing fails
        """
        if not xml_content or not xml_content.strip():
            raise ParsingError("Empty XML content provided")

        try:
            # Parse XML and find all entries
            import xml.etree.ElementTree as ElementTree

            root = ElementTree.fromstring(xml_content)
            entries = root.findall("atom:entry", self.extractor.namespace)

            papers = []
            for entry in entries:
                try:
                    paper = self._parse_entry_to_paper(entry)
                    papers.append(paper)
                except Exception as e:
                    logger.warning(f"Failed to parse entry: {e}")
                    continue

            return papers
        except Exception as e:
            logger.warning(f"Failed to parse XML response: {e}")
            return []

    def _parse_entry_to_paper(self, entry: Any) -> ArxivPaper:
        """Parse a single entry element into ArxivPaper using ArxivExtractor methods.

        Args:
            entry: XML entry element

        Returns:
            ArxivPaper instance
        """
        # Extract ArXiv ID from the entry ID
        entry_id = self.extractor._extract_text(entry, "atom:id")
        arxiv_id = entry_id.split("/")[-1] if entry_id else ""

        # Extract basic metadata using ArxivExtractor methods
        title = self.extractor._extract_text(entry, "atom:title")
        abstract = self.extractor._extract_text(entry, "atom:summary")
        authors = self.extractor._extract_authors(entry)
        categories = self.extractor._extract_categories(entry)
        published_date = self.extractor._extract_date(entry, "atom:published")
        updated_date = self.extractor._extract_date(entry, "atom:updated")

        # Determine primary category
        primary_category = categories[0] if categories else ""

        # Build URLs
        pdf_url = f"https://arxiv.org/pdf/{arxiv_id}"
        arxiv_url = f"https://arxiv.org/abs/{arxiv_id}"

        return ArxivPaper(
            arxiv_id=arxiv_id,
            title=title,
            abstract=abstract,
            authors=authors,
            categories=categories,
            primary_category=primary_category,
            published_date=published_date,
            updated_date=updated_date,
            url_pdf=pdf_url,
            url_abs=arxiv_url,
            doi=None,
            journal=None,
            volume=None,
            pages=None,
            keywords=[],
            raw_metadata={},
        )
