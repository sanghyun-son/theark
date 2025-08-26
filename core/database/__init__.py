"""Core database functionality."""

from .config import (
    DatabaseConfig,
    Environment,
    get_database_dir,
    get_database_path,
    setup_database_environment,
)
from .interfaces.manager import DatabaseManager
from .repository import (
    CrawlEventRepository,
    FeedRepository,
    LLMRequestRepository,
    PaperRepository,
    SummaryRepository,
    UserRepository,
)

__all__ = [
    "DatabaseManager",
    "DatabaseConfig",
    "Environment",
    "get_database_path",
    "get_database_dir",
    "setup_database_environment",
    "PaperRepository",
    "SummaryRepository",
    "UserRepository",
    "FeedRepository",
    "CrawlEventRepository",
    "LLMRequestRepository",
]
