"""Database module for the arXiv crawler."""

from .base import DatabaseManager
from .config import (
    DatabaseConfig,
    Environment,
    get_database_dir,
    get_database_path,
    setup_database_environment,
)
from .llm_db import LLMDatabaseManager, close_llm_db_manager, get_llm_db_manager
from .llm_models import LLMRequest, LLMUsageStats
from .llm_repository import LLMRequestRepository
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
    # LLM tracking
    "LLMDatabaseManager",
    "get_llm_db_manager",
    "close_llm_db_manager",
    "LLMRequest",
    "LLMUsageStats",
    "LLMRequestRepository",
]
