"""Base classes for paper extractors."""

from abc import ABC, abstractmethod

from core.models.domain.paper_extraction import PaperMetadata


class BaseExtractor(ABC):
    """Base class for all paper extractors."""

    @abstractmethod
    def can_extract(self, url: str) -> bool:
        """Check if this extractor can handle the given URL.

        Args:
            url: URL to check

        Returns:
            True if this extractor can handle the URL
        """
        pass

    @abstractmethod
    def extract_identifier(self, url: str) -> str:
        """Extract unique identifier from URL.

        Args:
            url: URL to extract identifier from

        Returns:
            Unique identifier for the paper

        Raises:
            ValueError: If URL format is invalid
        """
        pass

    @abstractmethod
    async def extract_metadata_async(self, url: str) -> PaperMetadata:
        """Extract paper metadata from URL asynchronously.

        Args:
            url: URL to extract metadata from

        Returns:
            Paper metadata

        Raises:
            ValueError: If extraction fails
        """
        pass

    def get_source_name(self) -> str:
        """Get the name of the source this extractor handles.

        Returns:
            Source name (e.g., 'ArXiv', 'PubMed')
        """
        return self.__class__.__name__.replace("Extractor", "")


class BaseSourceExplorer(ABC):
    """Base class for paper source exploration.

    This is for future implementation of bulk paper discovery.
    """

    @abstractmethod
    async def explore_recent(self, limit: int = 100) -> list[PaperMetadata]:
        """Explore recent papers from the source.

        Args:
            limit: Maximum number of papers to return

        Returns:
            List of recent paper metadata
        """
        pass

    @abstractmethod
    async def explore_by_category(
        self, category: str, limit: int = 100
    ) -> list[PaperMetadata]:
        """Explore papers by category.

        Args:
            category: Category to explore
            limit: Maximum number of papers to return

        Returns:
            List of paper metadata in the category
        """
        pass
