"""Tests for ArXivClient."""

import httpx
import pytest

from crawler.arxiv.client import ArxivClient
from crawler.arxiv.exceptions import ArxivAPIError, ArxivError


class TestArxivClient:
    """Test ArXivClient functionality."""

    def test_initialization(self, mock_arxiv_client):
        """Test client initialization."""
        client = mock_arxiv_client
        assert client.base_url.startswith("http://")
        assert client._client is None  # Private client should be None initially
        assert client.rate_limiter is not None
        # Client property should create client when accessed
        assert client.client is not None

    def test_initialization_custom_url(self):
        """Test client initialization with custom URL."""
        custom_url = "http://custom.arxiv.org/api/query"
        client = ArxivClient(base_url=custom_url)
        assert client.base_url == custom_url

    def test_extract_arxiv_id_direct(self, mock_arxiv_client):
        """Test extracting arXiv ID from direct ID."""
        client = mock_arxiv_client

        # Test direct arXiv ID
        assert client._extract_arxiv_id("1706.03762") == "1706.03762"
        assert client._extract_arxiv_id("2401.00123") == "2401.00123"

    def test_extract_arxiv_id_abstract_url(self, mock_arxiv_client):
        """Test extracting arXiv ID from abstract URLs."""
        client = mock_arxiv_client

        # Test abstract URLs
        assert (
            client._extract_arxiv_id("http://arxiv.org/abs/1706.03762") == "1706.03762"
        )
        assert (
            client._extract_arxiv_id("https://arxiv.org/abs/2401.00123") == "2401.00123"
        )
        assert client._extract_arxiv_id("arxiv.org/abs/1706.03762") == "1706.03762"

    def test_extract_arxiv_id_pdf_url(self, mock_arxiv_client):
        """Test extracting arXiv ID from PDF URLs."""
        client = mock_arxiv_client

        # Test PDF URLs
        assert (
            client._extract_arxiv_id("http://arxiv.org/pdf/1706.03762") == "1706.03762"
        )
        assert (
            client._extract_arxiv_id("https://arxiv.org/pdf/2401.00123") == "2401.00123"
        )
        assert client._extract_arxiv_id("arxiv.org/pdf/1706.03762") == "1706.03762"

    def test_extract_arxiv_id_with_version(self, mock_arxiv_client):
        """Test extracting arXiv ID from URLs with version numbers."""
        client = mock_arxiv_client

        # Test URLs with version numbers
        assert (
            client._extract_arxiv_id("http://arxiv.org/abs/1706.03762v7")
            == "1706.03762"
        )
        assert (
            client._extract_arxiv_id("https://arxiv.org/abs/2401.00123v1")
            == "2401.00123"
        )

    def test_extract_arxiv_id_invalid(self, mock_arxiv_client):
        """Test extracting arXiv ID from invalid inputs."""
        client = mock_arxiv_client

        # Test invalid inputs
        with pytest.raises(ArxivError, match="Could not extract arXiv ID"):
            client._extract_arxiv_id("invalid")

        with pytest.raises(ArxivError, match="Could not extract arXiv ID"):
            client._extract_arxiv_id("http://example.com")

        with pytest.raises(ArxivError, match="Could not extract arXiv ID"):
            client._extract_arxiv_id("1706.037")  # Too short

    @pytest.mark.asyncio
    async def test_client_creation(self, mock_arxiv_client):
        """Test client creation and HTTP client initialization."""
        client = mock_arxiv_client
        assert client.client is not None
        assert isinstance(client.client, httpx.AsyncClient)

    @pytest.mark.asyncio
    async def test_get_paper_success(self, mock_arxiv_client):
        """Test successful paper fetching."""
        # Test with direct ID
        response = await mock_arxiv_client.get_paper("1706.03762")
        assert "Attention Is All You Need" in response
        assert "Ashish Vaswani" in response
        assert "cs.CL" in response

        # Test with abstract URL
        response = await mock_arxiv_client.get_paper("http://arxiv.org/abs/1706.03762")
        assert "Attention Is All You Need" in response

        # Test with PDF URL
        response = await mock_arxiv_client.get_paper("http://arxiv.org/pdf/1706.03762")
        assert "Attention Is All You Need" in response

    @pytest.mark.asyncio
    async def test_get_paper_by_id(self, mock_arxiv_client):
        """Test get_paper_by_id method."""
        response = await mock_arxiv_client.get_paper_by_id("1706.03762")
        assert "Attention Is All You Need" in response

    @pytest.mark.asyncio
    async def test_get_paper_by_url(self, mock_arxiv_client):
        """Test get_paper_by_url method."""
        response = await mock_arxiv_client.get_paper_by_url(
            "http://arxiv.org/abs/1706.03762"
        )
        assert "Attention Is All You Need" in response

    @pytest.mark.asyncio
    async def test_get_paper_not_found(self, mock_arxiv_client):
        """Test paper not found scenario."""
        # arXiv API returns 200 with empty results for not found papers
        response = await mock_arxiv_client.get_paper("9999.99999")
        # Should return empty feed with totalResults=0
        assert "0</opensearch:totalResults>" in response

    @pytest.mark.asyncio
    async def test_get_paper_server_error(self, mock_arxiv_client):
        """Test server error scenario."""
        with pytest.raises(ArxivAPIError, match="HTTP 500"):
            await mock_arxiv_client.get_paper(
                "1706.99999"
            )  # This will trigger the error endpoint

    @pytest.mark.asyncio
    async def test_rate_limiting(self, mock_arxiv_client):
        """Test that rate limiting is applied."""
        import time

        start_time = time.time()

        # Make two requests - should be rate limited
        await mock_arxiv_client.get_paper("1706.03762")
        await mock_arxiv_client.get_paper("1706.03762")

        elapsed = time.time() - start_time

        # Should take at least 0.9 seconds due to rate limiting (1 request/second)
        assert elapsed >= 0.9

    @pytest.mark.asyncio
    async def test_user_agent_header(self, mock_arxiv_client):
        """Test that proper User-Agent header is set."""
        # The mock server doesn't validate headers, but we can verify the client is configured
        from crawler.arxiv.constants import DEFAULT_USER_AGENT

        assert mock_arxiv_client.client.headers["User-Agent"] == DEFAULT_USER_AGENT
