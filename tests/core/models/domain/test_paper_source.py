"""Tests for paper source enumeration."""

import pytest

from core.models.domain.paper_source import PaperSource


class TestPaperSource:
    """Test PaperSource enumeration."""

    def test_default_categories_arxiv(self) -> None:
        """Test default categories for arXiv source."""
        assert PaperSource.ARXIV.default_categories == ["cs.OTHER"]

    def test_default_categories_pubmed(self) -> None:
        """Test default categories for PubMed source."""
        assert PaperSource.PUBMED.default_categories == ["med.OTHER"]

    def test_default_categories_ieee(self) -> None:
        """Test default categories for IEEE source."""
        assert PaperSource.IEEE.default_categories == ["eng.OTHER"]

    def test_default_categories_custom(self) -> None:
        """Test default categories for custom source."""
        assert PaperSource.CUSTOM.default_categories == ["gen.OTHER"]

    def test_default_category_arxiv(self) -> None:
        """Test default category for arXiv source."""
        assert PaperSource.ARXIV.default_category == "cs.OTHER"

    def test_default_category_pubmed(self) -> None:
        """Test default category for PubMed source."""
        assert PaperSource.PUBMED.default_category == "med.OTHER"

    def test_default_category_ieee(self) -> None:
        """Test default category for IEEE source."""
        assert PaperSource.IEEE.default_category == "eng.OTHER"

    def test_default_category_custom(self) -> None:
        """Test default category for custom source."""
        assert PaperSource.CUSTOM.default_category == "gen.OTHER"

    def test_source_values(self) -> None:
        """Test source enum values."""
        assert PaperSource.ARXIV.value == "arxiv"
        assert PaperSource.PUBMED.value == "pubmed"
        assert PaperSource.IEEE.value == "ieee"
        assert PaperSource.CUSTOM.value == "custom"
