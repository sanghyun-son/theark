"""Paper extractors package."""

from core.extractors.base import BaseExtractor, BaseSourceExplorer
from core.extractors.exceptions import (
    ExtractionError,
    ExtractorError,
    InvalidIdentifierError,
    NetworkError,
    ParsingError,
    UnsupportedURLError,
)
from core.extractors.factory import ExtractorFactory, extractor_factory
from core.models.domain.paper_extraction import PaperMetadata

__all__ = [
    # Base classes
    "BaseExtractor",
    "BaseSourceExplorer",
    # Exceptions
    "ExtractorError",
    "ExtractionError",
    "InvalidIdentifierError",
    "NetworkError",
    "ParsingError",
    "UnsupportedURLError",
    # Factory
    "ExtractorFactory",
    "extractor_factory",
    # Models
    "PaperMetadata",
]
