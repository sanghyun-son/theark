"""Database module for the arXiv crawler."""

from core.database import DatabaseManager
from core.models import (
    CrawlEvent,
    FeedItem,
    LLMRequest,
    LLMUsageStats,
)
from core.models import PaperEntity as Paper
from core.models import SummaryEntity as Summary
from core.models import UserEntity as AppUser
from core.models import UserInterestEntity as UserInterest
from core.models import UserStarEntity as UserStar

from .config import (
    DatabaseConfig,
    Environment,
    get_database_dir,
    get_database_path,
    get_llm_database_path,
    setup_database_environment,
)
from .llm_repository import LLMRequestRepository
from .llm_sqlite_manager import LLMSQLiteManager
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
    "get_llm_database_path",
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
    "LLMSQLiteManager",
    "LLMRequest",
    "LLMUsageStats",
    "LLMRequestRepository",
]
