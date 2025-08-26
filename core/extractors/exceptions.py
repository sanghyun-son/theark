"""Exceptions for paper extractors."""


class ExtractorError(Exception):
    """Base exception for extractor errors."""

    pass


class UnsupportedURLError(ExtractorError):
    """Raised when an extractor cannot handle a given URL."""

    pass


class ExtractionError(ExtractorError):
    """Raised when paper extraction fails."""

    pass


class ParsingError(ExtractionError):
    """Raised when parsing paper metadata fails."""

    pass


class NetworkError(ExtractionError):
    """Raised when network requests fail."""

    pass


class InvalidIdentifierError(ExtractorError):
    """Raised when paper identifier is invalid."""

    pass
