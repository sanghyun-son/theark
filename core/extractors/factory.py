"""Simple factory for managing paper extractors."""

from core.extractors.base import BaseExtractor
from core.extractors.exceptions import UnsupportedURLError
from core.log import get_logger

logger = get_logger(__name__)

# Global extractor registry
_extractors: dict[str, BaseExtractor] = {}


def register_extractor(name: str, extractor: BaseExtractor) -> None:
    """Register a new extractor.

    Args:
        name: Name for the extractor
        extractor: Extractor instance
    """
    _extractors[name] = extractor
    logger.info(f"Registered extractor: {name}")


def get_extractor(name: str) -> BaseExtractor:
    """Get extractor by name.

    Args:
        name: Name of the extractor

    Returns:
        Extractor instance

    Raises:
        KeyError: If extractor not found
    """
    if name not in _extractors:
        raise KeyError(f"Extractor not found: {name}")
    return _extractors[name]


def find_extractor_for_url(url: str) -> BaseExtractor:
    """Find the appropriate extractor for a given URL.

    Args:
        url: URL to find extractor for

    Returns:
        Appropriate extractor

    Raises:
        UnsupportedURLError: If no extractor found for the URL
    """
    for extractor in _extractors.values():
        if extractor.can_extract(url):
            return extractor

    raise UnsupportedURLError(f"No extractor found for URL: {url}")


def get_all_extractors() -> dict[str, BaseExtractor]:
    """Get all registered extractors.

    Returns:
        Dictionary of all extractors
    """
    return _extractors.copy()


def get_supported_sources() -> list[str]:
    """Get list of supported source names.

    Returns:
        List of supported source names
    """
    return [extractor.get_source_name() for extractor in _extractors.values()]


# Legacy compatibility - simple object with methods
class ExtractorFactory:
    """Legacy compatibility class for extractor factory."""

    def register_extractor(self, name: str, extractor: BaseExtractor) -> None:
        register_extractor(name, extractor)

    def get_extractor(self, name: str) -> BaseExtractor:
        return get_extractor(name)

    def find_extractor_for_url(self, url: str) -> BaseExtractor:
        return find_extractor_for_url(url)

    def get_all_extractors(self) -> dict[str, BaseExtractor]:
        return get_all_extractors()

    def get_supported_sources(self) -> list[str]:
        return get_supported_sources()


# Global factory instance for backward compatibility
extractor_factory = ExtractorFactory()
