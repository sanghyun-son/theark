"""ArXiv API client for fetching papers."""

import re
from typing import Any

import httpx

from core import AsyncRateLimiter, get_logger
from .constants import (
    ARXIV_API_BASE_URL,
    DEFAULT_RATE_LIMIT,
    DEFAULT_TIMEOUT,
    DEFAULT_USER_AGENT,
)
from .exceptions import (
    ArxivError,
    ArxivNotFoundError,
    ArxivAPIError,
    ArxivTimeoutError,
)

logger = get_logger(__name__)


class ArxivClient:
    """ArXiv API client for fetching papers."""

    def __init__(self, base_url: str = ARXIV_API_BASE_URL):
        """Initialize ArXiv client.

        Args:
            base_url: Base URL for arXiv API
        """
        self.base_url = base_url
        self.client: httpx.AsyncClient | None = None
        self.rate_limiter = AsyncRateLimiter(requests_per_second=DEFAULT_RATE_LIMIT)

    async def __aenter__(self) -> "ArxivClient":
        """Async context manager entry."""
        self.client = httpx.AsyncClient(
            timeout=httpx.Timeout(DEFAULT_TIMEOUT),
            limits=httpx.Limits(max_keepalive_connections=5, max_connections=10),
            headers={"User-Agent": DEFAULT_USER_AGENT},
        )
        return self

    async def __aexit__(
        self,
        exc_type: type[BaseException] | None,
        exc_val: BaseException | None,
        exc_tb: Any,
    ) -> None:
        """Async context manager exit."""
        if self.client:
            await self.client.aclose()

    def _extract_arxiv_id(self, identifier: str) -> str:
        """Extract arXiv ID from various input formats.

        Args:
            identifier: arXiv ID, abstract URL, or PDF URL

        Returns:
            Clean arXiv ID (e.g., "1706.03762")

        Raises:
            ArxivError: If arXiv ID cannot be extracted
        """
        # Handle direct arXiv ID
        if re.match(r"^\d{4}\.\d{4,5}$", identifier):
            return identifier

        # Handle abstract URLs
        abs_match = re.search(r"arxiv\.org/abs/(\d{4}\.\d{4,5})", identifier)
        if abs_match:
            return abs_match.group(1)

        # Handle PDF URLs
        pdf_match = re.search(r"arxiv\.org/pdf/(\d{4}\.\d{4,5})", identifier)
        if pdf_match:
            return pdf_match.group(1)

        # Handle full URLs with version numbers
        version_match = re.search(r"arxiv\.org/abs/(\d{4}\.\d{4,5})v\d+", identifier)
        if version_match:
            return version_match.group(1)

        raise ArxivError(f"Could not extract arXiv ID from: {identifier}")

    async def get_paper(self, identifier: str) -> str:
        """Fetch paper metadata from arXiv API.

        Args:
            identifier: arXiv ID, abstract URL, or PDF URL

        Returns:
            XML response as string

        Raises:
            ArxivNotFoundError: If paper not found
            ArxivAPIError: If API request fails
            ArxivTimeoutError: If request times out
        """
        if not self.client:
            raise RuntimeError("Client not initialized. Use async context manager.")

        # Extract arXiv ID from various input formats
        arxiv_id = self._extract_arxiv_id(identifier)
        logger.info(f"Fetching paper: {arxiv_id}")

        # Rate limit before API call
        await self.rate_limiter.wait()

        params = httpx.QueryParams(
            {
                "id_list": arxiv_id,
                "start": 0,
                "max_results": 1,
            }
        )

        try:
            response = await self.client.get(self.base_url, params=params)
            response.raise_for_status()

            logger.info(f"Successfully fetched paper {arxiv_id}")
            return response.text

        except httpx.HTTPStatusError as e:
            if e.response.status_code == 404:
                logger.warning(f"Paper {arxiv_id} not found")
                raise ArxivNotFoundError(f"Paper {arxiv_id} not found")
            else:
                logger.error(f"HTTP error fetching {arxiv_id}: {e}")
                raise ArxivAPIError(f"HTTP {e.response.status_code}: {e}")

        except httpx.TimeoutException:
            logger.error(f"Timeout fetching paper {arxiv_id}")
            raise ArxivTimeoutError(f"Timeout fetching {arxiv_id}")

        except httpx.RequestError as e:
            logger.error(f"Request error fetching {arxiv_id}: {e}")
            raise ArxivAPIError(f"Request failed: {e}")

    async def get_paper_by_id(self, arxiv_id: str) -> str:
        """Fetch paper by arXiv ID.

        Args:
            arxiv_id: arXiv ID (e.g., "1706.03762")

        Returns:
            XML response as string
        """
        return await self.get_paper(arxiv_id)

    async def get_paper_by_url(self, url: str) -> str:
        """Fetch paper by arXiv URL.

        Args:
            url: arXiv abstract or PDF URL

        Returns:
            XML response as string
        """
        return await self.get_paper(url)
