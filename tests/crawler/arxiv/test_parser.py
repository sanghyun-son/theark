"""Tests for ArXivParser."""

from xml.etree import ElementTree

import pytest

from crawler.arxiv.parser import ArxivParser
from crawler.database import Paper


class TestArxivParser:
    """Test ArxivParser functionality."""

    @pytest.fixture
    def parser(self):
        """Create a parser instance for testing."""
        return ArxivParser()

    @pytest.fixture
    def mock_arxiv_server(self, httpserver):
        """Use the shared mock arXiv server."""
        # The mock server is already set up in conftest.py
        return httpserver

    @pytest.fixture
    def sample_xml(self):
        """Sample XML response from arXiv API."""
        from tests.shared_test_data import SAMPLE_PAPER_XML

        return SAMPLE_PAPER_XML

    def test_initialization(self, parser):
        """Test parser initialization."""
        from crawler.arxiv.constants import ARXIV_NAMESPACES

        assert parser.namespace == ARXIV_NAMESPACES

    def test_parse_paper_success(self, parser, sample_xml):
        """Test successful paper parsing."""
        paper = parser.parse_paper(sample_xml)

        assert paper is not None
        assert isinstance(paper, Paper)
        assert paper.arxiv_id == "1706.03762"
        assert paper.title == "Attention Is All You Need"
        assert "Transformer" in paper.abstract
        assert paper.authors == "Ashish Vaswani;Noam Shazeer;Niki Parmar"
        assert paper.primary_category == "cs.CL"
        assert paper.categories == "cs.CL,cs.LG"
        assert paper.url_abs == "https://arxiv.org/abs/1706.03762"
        assert paper.url_pdf == "https://arxiv.org/pdf/1706.03762"
        # Note: Paper model doesn't include doi and comments fields

    def test_parse_paper_no_entries(self, parser):
        """Test parsing XML with no entries."""
        from tests.shared_test_data import EMPTY_FEED_XML

        paper = parser.parse_paper(EMPTY_FEED_XML)
        assert paper is None

    def test_parse_paper_invalid_xml(self, parser):
        """Test parsing invalid XML."""
        xml = "invalid xml content"

        paper = parser.parse_paper(xml)
        assert paper is None

    def test_parse_paper_missing_fields(self, parser):
        """Test parsing paper with missing optional fields."""
        xml = """<?xml version="1.0" encoding="UTF-8"?>
<feed xmlns="http://www.w3.org/2005/Atom" xmlns:arxiv="http://arxiv.org/schemas/atom">
  <entry>
    <id>http://arxiv.org/abs/1706.03762</id>
    <title>Test Paper</title>
    <summary>Test abstract</summary>
    <arxiv:primary_category xmlns:arxiv="http://arxiv.org/schemas/atom" term="cs.AI" />
  </entry>
</feed>"""

        paper = parser.parse_paper(xml)

        assert paper is not None
        assert paper.arxiv_id == "1706.03762"
        assert paper.title == "Test Paper"
        assert paper.abstract == "Test abstract"
        assert paper.authors == ""  # Missing authors
        assert paper.primary_category == "cs.AI"
        assert paper.categories == "cs.AI"
        # Note: Paper model doesn't include doi and comments fields

    def test_extract_arxiv_id_from_id_element(self, parser):
        """Test extracting arXiv ID from id element."""
        entry = ElementTree.fromstring(
            """
        <entry xmlns="http://www.w3.org/2005/Atom">
            <id>http://arxiv.org/abs/1706.03762</id>
        </entry>
        """
        )

        arxiv_id = parser._extract_arxiv_id(entry)
        assert arxiv_id == "1706.03762"

    def test_extract_arxiv_id_from_primary_category(self, parser):
        """Test extracting arXiv ID from primary category term."""
        entry = ElementTree.fromstring(
            """
        <entry xmlns="http://www.w3.org/2005/Atom" xmlns:arxiv="http://arxiv.org/schemas/atom">
            <arxiv:primary_category term="http://arxiv.org/abs/1706.03762" />
        </entry>
        """
        )

        arxiv_id = parser._extract_arxiv_id(entry)
        assert arxiv_id == "1706.03762"

    def test_extract_arxiv_id_failure(self, parser):
        """Test extracting arXiv ID when not available."""
        entry = ElementTree.fromstring(
            """
        <entry xmlns="http://www.w3.org/2005/Atom">
            <title>Test Paper</title>
        </entry>
        """
        )

        with pytest.raises(ValueError, match="Could not extract arXiv ID"):
            parser._extract_arxiv_id(entry)

    def test_extract_authors(self, parser):
        """Test extracting authors."""
        entry = ElementTree.fromstring(
            """
        <entry xmlns="http://www.w3.org/2005/Atom">
            <author><name>Author 1</name></author>
            <author><name>Author 2</name></author>
        </entry>
        """
        )

        authors = parser._extract_authors(entry)
        assert authors == "Author 1;Author 2"

    def test_extract_authors_empty(self, parser):
        """Test extracting authors when none exist."""
        entry = ElementTree.fromstring(
            """
        <entry xmlns="http://www.w3.org/2005/Atom">
            <title>Test Paper</title>
        </entry>
        """
        )

        authors = parser._extract_authors(entry)
        assert authors == ""

    def test_extract_categories(self, parser):
        """Test extracting categories."""
        entry = ElementTree.fromstring(
            """
        <entry xmlns="http://www.w3.org/2005/Atom" xmlns:arxiv="http://arxiv.org/schemas/atom">
            <arxiv:primary_category term="cs.CL" />
            <category term="cs.LG" />
            <category term="cs.AI" />
        </entry>
        """
        )

        categories = parser._extract_categories(entry)
        assert categories == "cs.CL,cs.LG,cs.AI"

    def test_extract_categories_duplicates(self, parser):
        """Test extracting categories with duplicates."""
        entry = ElementTree.fromstring(
            """
        <entry xmlns="http://www.w3.org/2005/Atom" xmlns:arxiv="http://arxiv.org/schemas/atom">
            <arxiv:primary_category term="cs.CL" />
            <category term="cs.CL" />
            <category term="cs.LG" />
        </entry>
        """
        )

        categories = parser._extract_categories(entry)
        assert categories == "cs.CL,cs.LG"  # Duplicate removed

    def test_extract_date_valid(self, parser):
        """Test extracting valid date."""
        entry = ElementTree.fromstring(
            """
        <entry xmlns="http://www.w3.org/2005/Atom">
            <published>2017-06-12T18:00:00Z</published>
        </entry>
        """
        )

        date = parser._extract_date(entry, "atom:published")
        # The parser converts to YYYY-MM-DDTHH:MM:SSZ format
        assert date == "2017-06-12T18:00:00Z"

    def test_extract_date_invalid(self, parser):
        """Test extracting invalid date."""
        entry = ElementTree.fromstring(
            """
        <entry xmlns="http://www.w3.org/2005/Atom">
            <published>invalid-date</published>
        </entry>
        """
        )

        date = parser._extract_date(entry, "atom:published")
        # Should return current time in ISO format
        assert "Z" in date
        assert "T" in date

    def test_extract_doi_from_link(self, parser):
        """Test extracting DOI from link."""
        entry = ElementTree.fromstring(
            """
        <entry xmlns="http://www.w3.org/2005/Atom">
            <link href="https://doi.org/10.48550/arXiv.1706.03762" />
        </entry>
        """
        )

        doi = parser._extract_doi(entry)
        assert doi == "https://doi.org/10.48550/arXiv.1706.03762"

    def test_extract_doi_from_arxiv_element(self, parser):
        """Test extracting DOI from arxiv:doi element."""
        entry = ElementTree.fromstring(
            """
        <entry xmlns="http://www.w3.org/2005/Atom" xmlns:arxiv="http://arxiv.org/schemas/atom">
            <arxiv:doi>10.48550/arXiv.1706.03762</arxiv:doi>
        </entry>
        """
        )

        doi = parser._extract_doi(entry)
        assert doi == "10.48550/arXiv.1706.03762"

    def test_extract_comments(self, parser):
        """Test extracting comments."""
        entry = ElementTree.fromstring(
            """
        <entry xmlns="http://www.w3.org/2005/Atom" xmlns:arxiv="http://arxiv.org/schemas/atom">
            <arxiv:comment>NIPS 2017</arxiv:comment>
        </entry>
        """
        )

        comments = parser._extract_comments(entry)
        assert comments == "NIPS 2017"

    def test_extract_comments_none(self, parser):
        """Test extracting comments when none exist."""
        entry = ElementTree.fromstring(
            """
        <entry xmlns="http://www.w3.org/2005/Atom">
            <title>Test Paper</title>
        </entry>
        """
        )

        comments = parser._extract_comments(entry)
        assert comments is None

    def test_parse_paper_with_mock_server(self, parser, mock_arxiv_server):
        """Test parsing paper using mock arXiv server."""
        from tests.shared_test_data import DETAILED_PAPER_XML

        paper = parser.parse_paper(DETAILED_PAPER_XML)

        assert paper is not None
        assert paper.arxiv_id == "1706.03762"
        assert paper.title == "Attention Is All You Need"
        assert "Transformer" in paper.abstract
        assert (
            paper.authors
            == "Ashish Vaswani;Noam Shazeer;Niki Parmar;Jakob Uszkoreit;Llion Jones;Aidan N. Gomez;Lukasz Kaiser;Illia Polosukhin"
        )
        assert paper.primary_category == "cs.CL"
        assert paper.categories == "cs.CL,cs.LG"
