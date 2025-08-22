"""Database module for the arXiv crawler."""

from .base import DatabaseManager
from .config import (
    DatabaseConfig,
    Environment,
    get_database_dir,
    get_database_path,
    setup_database_environment,
)
from .models import (
    AppUser,
    CrawlEvent,
    FeedItem,
    Paper,
    Summary,
    UserInterest,
    UserStar,
)
from .repository import (
    CrawlEventRepository,
    FeedRepository,
    PaperRepository,
    SummaryRepository,
    UserRepository,
)
from .sqlite_manager import SQLiteManager

__all__ = [
    "DatabaseManager",
    "SQLiteManager",
    "DatabaseConfig",
    "Environment",
    "get_database_path",
    "get_database_dir",
    "setup_database_environment",
    "Paper",
    "Summary",
    "AppUser",
    "UserInterest",
    "UserStar",
    "FeedItem",
    "CrawlEvent",
    "PaperRepository",
    "SummaryRepository",
    "UserRepository",
    "FeedRepository",
    "CrawlEventRepository",
]
