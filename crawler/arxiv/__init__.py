"""arXiv crawler module."""

from .exceptions import (
    ArxivError,
    ArxivNotFoundError,
    ArxivAPIError,
    ArxivTimeoutError,
    ArxivRateLimitError,
)
from .client import ArxivClient
from .parser import ArxivParser
from .crawler import (
    ArxivCrawler,
    CrawlStatus,
    CrawlConfig,
    OnDemandCrawlConfig,
    PeriodicCrawlConfig,
)

__all__ = [
    "ArxivError",
    "ArxivNotFoundError",
    "ArxivAPIError",
    "ArxivTimeoutError",
    "ArxivRateLimitError",
    "ArxivClient",
    "ArxivParser",
    "ArxivCrawler",
    "CrawlStatus",
    "CrawlConfig",
    "OnDemandCrawlConfig",
    "PeriodicCrawlConfig",
]
