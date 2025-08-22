"""Custom exceptions for arXiv crawler."""


class ArxivError(Exception):
    """Base exception for arXiv-related errors."""

    pass


class ArxivNotFoundError(ArxivError):
    """Raised when a paper is not found on arXiv."""

    pass


class ArxivAPIError(ArxivError):
    """Raised when there's an error with the arXiv API."""

    pass


class ArxivTimeoutError(ArxivError):
    """Raised when an arXiv API request times out."""

    pass


class ArxivRateLimitError(ArxivError):
    """Raised when rate limits are exceeded."""

    pass
