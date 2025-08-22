"""arXiv crawler module."""

from .client import ArxivClient
from .crawler import ArxivCrawler, CrawlConfig, CrawlStatus
from .exceptions import (
    ArxivAPIError,
    ArxivError,
    ArxivNotFoundError,
    ArxivRateLimitError,
    ArxivTimeoutError,
)
from .on_demand_crawler import OnDemandCrawlConfig
from .parser import ArxivParser
from .periodic_crawler import PeriodicCrawlConfig

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
