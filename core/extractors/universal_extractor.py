"""Universal paper extractor that delegates to source-specific extractors."""

from core.extractors.arxiv_extractor import ArxivExtractor
from core.models.domain.paper_extraction import PaperExtractor, PaperMetadata


class UniversalPaperExtractor:
    """Universal paper extractor that delegates to source-specific extractors."""

    def __init__(self) -> None:
        """Initialize universal paper extractor."""
        self.extractors: list[PaperExtractor] = []
        self._register_default_extractors()

    def register_extractor(self, extractor: PaperExtractor) -> None:
        """Register a new paper extractor."""
        self.extractors.append(extractor)

    def extract_paper(self, url: str) -> tuple[str, PaperMetadata]:
        """Extract paper identifier and metadata from URL.

        Args:
            url: URL to extract paper from

        Returns:
            Tuple of (identifier, metadata)

        Raises:
            ValueError: If no extractor found for the URL
        """
        for extractor in self.extractors:
            if extractor.can_extract(url):
                identifier = extractor.extract_identifier(url)
                metadata = extractor.extract_metadata(url)
                return identifier, metadata

        raise ValueError(f"No extractor found for URL: {url}")

    def get_supported_sources(self) -> list[str]:
        """Get list of supported source domains."""
        sources = []
        for extractor in self.extractors:
            if hasattr(extractor, "get_source_name"):
                sources.append(extractor.get_source_name())
            else:
                sources.append(extractor.__class__.__name__)
        return sources

    def _register_default_extractors(self) -> None:
        """Register default extractors."""
        self.register_extractor(ArxivExtractor())
