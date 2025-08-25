"""ArXiv-specific paper extractor."""

import re

from core.models.domain.paper_extraction import PaperExtractor, PaperMetadata
from crawler.arxiv.client import ArxivClient
from crawler.arxiv.parser import ArxivParser


class ArxivExtractor(PaperExtractor):
    """ArXiv-specific paper extractor."""

    def __init__(self) -> None:
        """Initialize ArXiv extractor."""
        self.client = ArxivClient()
        self.parser = ArxivParser()

    def can_extract(self, url: str) -> bool:
        """Check if this extractor can handle the given URL."""
        return "arxiv.org" in url

    def extract_identifier(self, url: str) -> str:
        """Extract arXiv identifier from URL."""
        match = re.search(r"arxiv\.org/(?:abs|pdf)/(\d{4}\.\d{4,5})", url)
        if not match:
            raise ValueError("Invalid arXiv URL format")
        return match.group(1)

    def extract_metadata(self, url: str) -> PaperMetadata:
        """Extract metadata from arXiv URL."""
        identifier = self.extract_identifier(url)

        # Use existing ArxivClient logic (sync version for now)
        xml_response = self._get_paper_sync(identifier)

        # Parse using existing ArxivParser logic
        paper_entity = self.parser.parse_paper(xml_response)

        if not paper_entity:
            raise ValueError(f"Failed to parse arXiv paper: {identifier}")

        return PaperMetadata(
            title=paper_entity.title,
            abstract=paper_entity.abstract,
            authors=paper_entity.authors.split(";"),
            published_date=paper_entity.published_at,
            updated_date=paper_entity.updated_at,
            url_abs=paper_entity.url_abs,
            url_pdf=paper_entity.url_pdf,
            categories=(
                paper_entity.categories.split(",") if paper_entity.categories else []
            ),
            doi=None,
            journal=None,
            volume=None,
            pages=None,
            raw_metadata={"arxiv_id": identifier},
        )

    def _get_paper_sync(self, identifier: str) -> str:
        """Synchronous version of get_paper for compatibility."""
        import asyncio

        try:
            loop = asyncio.get_event_loop()
            if loop.is_running():
                # If we're in an async context, we need to handle this differently
                # For now, we'll use a simple approach
                return self._get_paper_sync_simple(identifier)
            else:
                return loop.run_until_complete(self.client.get_paper(identifier))
        except RuntimeError:
            # No event loop, create one
            return asyncio.run(self.client.get_paper(identifier))

    def _get_paper_sync_simple(self, identifier: str) -> str:
        """Simple synchronous paper fetching."""
        # This is a simplified version - in production, you'd want proper async handling
        import httpx

        base_url = self.client.base_url
        params = {
            "id_list": identifier,
            "start": "0",
            "max_results": "1",
        }

        with httpx.Client() as client:
            response = client.get(base_url, params=params)
            response.raise_for_status()
            return response.text
