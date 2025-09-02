"""Tests for ArXiv source explorer."""

from unittest.mock import Mock, patch

import pytest

from core.extractors.concrete.arxiv_source_explorer import ArxivSourceExplorer
from core.extractors.exceptions import ParsingError
from core.models.domain.arxiv import ArxivPaper
from tests.shared_test_data import ARXIV_RESPONSES


@pytest.mark.asyncio
async def test_explore_recent_papers(
    mock_arxiv_source_explorer: ArxivSourceExplorer,
) -> None:
    """Test exploring recent papers."""
    with patch.object(
        mock_arxiv_source_explorer, "_explore_with_query"
    ) as mock_explore:
        mock_explore.return_value = []

        result = await mock_arxiv_source_explorer.explore_recent(limit=50, days_back=7)

        assert result == []
        mock_explore.assert_called_once()
        # Check that the query includes the correct date range
        call_args = mock_explore.call_args[0]
        assert "submittedDate:" in call_args[0]
        # The format is now YYYYMMDDHHMM+TO+YYYYMMDDHHMM
        assert "+TO+" in call_args[0]


@pytest.mark.asyncio
async def test_explore_by_category(
    mock_arxiv_source_explorer: ArxivSourceExplorer,
) -> None:
    """Test exploring papers by category."""
    with patch.object(
        mock_arxiv_source_explorer, "_explore_with_query"
    ) as mock_explore:
        mock_explore.return_value = []

        result = await mock_arxiv_source_explorer.explore_by_category("cs.AI", limit=20)

        assert result == []
        mock_explore.assert_called_once_with("cat:cs.AI", 20)


@pytest.mark.asyncio
async def test_explore_new_papers_by_category(
    mock_arxiv_source_explorer: ArxivSourceExplorer,
) -> None:
    """Test exploring new papers by category."""
    with patch.object(
        mock_arxiv_source_explorer, "_explore_papers_with_query"
    ) as mock_explore:
        mock_explore.return_value = []

        result = await mock_arxiv_source_explorer.explore_new_papers_by_category(
            category="cs.AI", start_date="2024-01-01", start_index=0, limit=10
        )

        assert result == []
        mock_explore.assert_called_once()
        call_args = mock_explore.call_args[0]
        # Format: submittedDate:[202401010000+TO+202401020000]+AND+cat:cs.AI
        assert (
            call_args[0] == "submittedDate:[202401010000+TO+202401020000]+AND+cat:cs.AI"
        )
        assert call_args[1] == 0  # start_index
        assert call_args[2] == 10  # limit


@pytest.mark.asyncio
async def test_explore_new_papers_by_category_with_mock(
    mock_arxiv_source_explorer: ArxivSourceExplorer,
) -> None:
    """Test exploring new papers by category using mock server."""
    result = await mock_arxiv_source_explorer.explore_new_papers_by_category(
        category="cs.AI", start_date="2025-01-01", start_index=0, limit=10
    )

    # Verify that we got papers from the mock response
    assert len(result) > 0

    # Check that all papers have cs.AI in their categories
    for paper in result:
        assert (
            "cs.AI" in paper.categories
        ), f"Paper {paper.arxiv_id} should have cs.AI category"


@pytest.mark.asyncio
async def test_explore_historical_papers_by_category(
    mock_arxiv_source_explorer: ArxivSourceExplorer,
) -> None:
    """Test exploring historical papers by category."""
    with patch.object(
        mock_arxiv_source_explorer, "_explore_papers_with_query"
    ) as mock_explore:
        mock_explore.return_value = []

        result = await mock_arxiv_source_explorer.explore_historical_papers_by_category(
            category="cs.AI", date="2020-01-01", start_index=0, limit=10
        )

        assert result == []
        mock_explore.assert_called_once()
        call_args = mock_explore.call_args[0]
        # Format: submittedDate:[202001010000+TO+202001012359]+AND+cat:cs.AI
        assert (
            call_args[0] == "submittedDate:[202001010000+TO+202001012359]+AND+cat:cs.AI"
        )
        assert call_args[1] == 0  # start_index
        assert call_args[2] == 10  # limit


@pytest.mark.asyncio
async def test_fetch_papers_batch_success(
    mock_arxiv_source_explorer: ArxivSourceExplorer,
) -> None:
    """Test successful batch fetching."""
    with patch("httpx.AsyncClient") as mock_client:
        mock_response = Mock()
        mock_response.text = ARXIV_RESPONSES["new_papers_cs_ai"]
        mock_response.raise_for_status.return_value = None
        mock_client.return_value.__aenter__.return_value.get.return_value = (
            mock_response
        )

        result = await mock_arxiv_source_explorer._fetch_papers_batch(
            query="cat:cs.AI", start=0, max_results=10
        )

        assert len(result) == 2
        assert result[0].arxiv_id == "2401.00001"
        assert result[0].title == "Recent Advances in Machine Learning"
        assert result[1].arxiv_id == "2401.00002"
        assert result[1].title == "Neural Network Optimization"


@pytest.mark.asyncio
async def test_fetch_papers_batch_network_error(
    mock_arxiv_source_explorer: ArxivSourceExplorer,
) -> None:
    """Test network error handling."""
    with patch("httpx.AsyncClient") as mock_client:
        mock_client.return_value.__aenter__.return_value.get.side_effect = Exception(
            "Network error"
        )

        with pytest.raises(Exception):
            await mock_arxiv_source_explorer._fetch_papers_batch(
                query="cat:cs.AI", start=0, max_results=10
            )


def test_parse_xml_response_success(
    mock_arxiv_source_explorer: ArxivSourceExplorer,
) -> None:
    """Test successful XML parsing."""
    xml_content = ARXIV_RESPONSES["new_papers_cs_ai"]
    result = mock_arxiv_source_explorer._parse_xml_response(xml_content)

    assert len(result) == 2
    assert result[0].arxiv_id == "2401.00001"
    assert result[0].title == "Recent Advances in Machine Learning"
    assert result[0].primary_category == "cs.AI"
    assert "cs.AI" in result[0].categories
    # Note: The XML only has cs.AI and cs.LG categories, but the parsing might only get cs.AI
    assert len(result[0].authors) == 2
    assert "John Doe" in result[0].authors
    assert "Jane Smith" in result[0].authors


def test_parse_xml_response_empty(
    mock_arxiv_source_explorer: ArxivSourceExplorer,
) -> None:
    """Test parsing empty XML response."""
    with pytest.raises(ParsingError):
        mock_arxiv_source_explorer._parse_xml_response("")


def test_parse_xml_response_invalid(
    mock_arxiv_source_explorer: ArxivSourceExplorer,
) -> None:
    """Test parsing invalid XML response."""
    # The method now catches exceptions and returns empty list instead of raising
    result = mock_arxiv_source_explorer._parse_xml_response("invalid xml content")
    assert result == []


def test_parse_entry_to_paper(mock_arxiv_source_explorer: ArxivSourceExplorer) -> None:
    """Test parsing single entry to paper."""
    import xml.etree.ElementTree as ElementTree

    # Create a mock entry element
    xml_content = ARXIV_RESPONSES["new_papers_cs_ai"]
    root = ElementTree.fromstring(xml_content)
    entry = root.find("atom:entry", mock_arxiv_source_explorer.extractor.namespace)

    result = mock_arxiv_source_explorer._parse_entry_to_paper(entry)

    assert result.arxiv_id == "2401.00001"
    assert result.title == "Recent Advances in Machine Learning"
    assert result.primary_category == "cs.AI"
    assert result.url_pdf == "https://arxiv.org/pdf/2401.00001"
    assert result.url_abs == "https://arxiv.org/abs/2401.00001"


@pytest.mark.asyncio
async def test_explore_with_query_pagination(
    mock_arxiv_source_explorer: ArxivSourceExplorer,
) -> None:
    """Test pagination in explore with query."""
    with patch.object(mock_arxiv_source_explorer, "_fetch_papers_batch") as mock_fetch:
        # First call returns 5 papers, second call returns 3 papers
        mock_fetch.side_effect = [
            [
                ArxivPaper(
                    arxiv_id=f"test{i}",
                    title=f"Paper {i}",
                    abstract="",
                    authors=[],
                    categories=[],
                    primary_category="cs.AI",
                    published_date="",
                    updated_date="",
                    url_pdf="",
                    url_abs="",
                )
                for i in range(5)
            ],
            [
                ArxivPaper(
                    arxiv_id=f"test{i}",
                    title=f"Paper {i}",
                    abstract="",
                    authors=[],
                    categories=[],
                    primary_category="cs.AI",
                    published_date="",
                    updated_date="",
                    url_pdf="",
                    url_abs="",
                )
                for i in range(5, 8)
            ],
            [],  # No more papers
        ]

        result = await mock_arxiv_source_explorer._explore_with_query(
            "cat:cs.AI", limit=10
        )

        assert len(result) == 8
        assert mock_fetch.call_count == 3
        # Check that start index increases correctly
        # The arguments are positional, not keyword arguments
        assert mock_fetch.call_args_list[0][0][1] == 0  # start index
        assert mock_fetch.call_args_list[1][0][1] == 5  # start index
        assert mock_fetch.call_args_list[2][0][1] == 8  # start index


# Mock server tests
@pytest.mark.asyncio
async def test_arxiv_category_search_mock(mock_arxiv_source_explorer):
    """Test that ArXiv category search returns the expected mock response."""
    # Test the specific search query that should return our example XML
    papers = await mock_arxiv_source_explorer.explore_new_papers_by_category(
        category="cs.AI",
        start_date="2025-01-01",
        start_index=0,
        limit=10,
    )

    # Verify that we got papers from the mock response
    assert len(papers) > 0

    # Check that the first paper has the expected structure
    first_paper = papers[0]
    assert first_paper.arxiv_id == "2501.00961v3"
    assert (
        first_paper.title
        == "Uncovering Memorization Effect in the Presence of Spurious Correlations"
    )
    assert first_paper.primary_category == "cs.LG"

    # Debug: print actual categories to see what's being parsed
    print(f"First paper categories: {first_paper.categories}")

    # Check that all papers have cs.AI in their categories (since we searched for cs.AI)
    for paper in papers:
        print(f"Paper {paper.arxiv_id} categories: {paper.categories}")
        assert (
            "cs.AI" in paper.categories
        ), f"Paper {paper.arxiv_id} should have cs.AI category"
