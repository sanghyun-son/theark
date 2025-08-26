"""Universal paper extraction domain models."""

from abc import ABC, abstractmethod
from typing import Any, Protocol

from pydantic import BaseModel, Field


class PaperMetadata(BaseModel):
    """Universal paper metadata structure."""

    title: str = Field(..., description="Paper title")
    abstract: str = Field(..., description="Paper abstract")
    authors: list[str] = Field(default_factory=list, description="List of authors")
    published_date: str = Field(..., description="Publication date")
    updated_date: str = Field(..., description="Last updated date")
    url_abs: str = Field(..., description="Abstract URL")
    url_pdf: str | None = Field(None, description="PDF URL")
    categories: list[str] = Field(default_factory=list, description="Paper categories")
    keywords: list[str] = Field(default_factory=list, description="Paper keywords")
    doi: str | None = Field(None, description="DOI")
    journal: str | None = Field(None, description="Journal name")
    volume: str | None = Field(None, description="Journal volume")
    pages: str | None = Field(None, description="Page numbers")
    raw_metadata: dict[str, Any] = Field(
        default_factory=dict, description="Source-specific raw data"
    )


class PaperExtractor(Protocol):
    """Protocol for paper extractors."""

    def can_extract(self, url: str) -> bool:
        """Check if this extractor can handle the given URL."""
        ...

    def extract_identifier(self, url: str) -> str:
        """Extract unique identifier from URL."""
        ...

    def extract_metadata(self, url: str) -> PaperMetadata:
        """Extract paper metadata from URL."""
        ...


class PaperSourceExplorer(ABC):
    """Abstract base class for paper source exploration."""

    @abstractmethod
    async def walk(self, start_url: str | None = None) -> Any:
        """Walk through paper source and yield papers.

        Args:
            start_url: Starting URL for exploration (optional)

        Yields:
            PaperMetadata objects
        """
        pass
