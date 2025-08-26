"""Factory for creating and managing paper extractors."""

from typing import Dict

from core.extractors.base import BaseExtractor
from core.extractors.exceptions import UnsupportedURLError
from core.log import get_logger

logger = get_logger(__name__)


class ExtractorFactory:
    """Factory for creating and managing paper extractors."""

    def __init__(self) -> None:
        """Initialize extractor factory."""
        self._extractors: Dict[str, BaseExtractor] = {}
        self._register_default_extractors()

    def register_extractor(self, name: str, extractor: BaseExtractor) -> None:
        """Register a new extractor.

        Args:
            name: Name for the extractor
            extractor: Extractor instance
        """
        self._extractors[name] = extractor
        logger.info(f"Registered extractor: {name}")

    def get_extractor(self, name: str) -> BaseExtractor:
        """Get extractor by name.

        Args:
            name: Name of the extractor

        Returns:
            Extractor instance

        Raises:
            KeyError: If extractor not found
        """
        if name not in self._extractors:
            raise KeyError(f"Extractor not found: {name}")
        return self._extractors[name]

    def find_extractor_for_url(self, url: str) -> BaseExtractor:
        """Find the appropriate extractor for a given URL.

        Args:
            url: URL to find extractor for

        Returns:
            Appropriate extractor

        Raises:
            UnsupportedURLError: If no extractor found for the URL
        """
        for extractor in self._extractors.values():
            if extractor.can_extract(url):
                return extractor

        raise UnsupportedURLError(f"No extractor found for URL: {url}")

    def get_all_extractors(self) -> Dict[str, BaseExtractor]:
        """Get all registered extractors.

        Returns:
            Dictionary of all extractors
        """
        return self._extractors.copy()

    def get_supported_sources(self) -> list[str]:
        """Get list of supported source names.

        Returns:
            List of supported source names
        """
        return [extractor.get_source_name() for extractor in self._extractors.values()]

    def _register_default_extractors(self) -> None:
        """Register default extractors."""
        # Note: Default extractors should be registered by the user
        # to allow for dependency injection
        pass


# Global factory instance
extractor_factory = ExtractorFactory()
