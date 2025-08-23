"""Shared LLM request database manager."""

import os
from pathlib import Path
from typing import Any

from core import get_logger

from .llm_repository import LLMRequestRepository
from .sqlite_manager import SQLiteManager

logger = get_logger(__name__)


class LLMDatabaseManager:
    """Shared database manager for LLM request tracking."""

    def __init__(self, db_path: str | None = None):
        """Initialize LLM database manager.

        Args:
            db_path: Optional path to database file. If None, uses shared location.
        """
        if db_path is None:
            db_path = self._get_default_db_path()

        self.db_path = Path(db_path)
        self._ensure_directory_exists()

        self.db_manager = SQLiteManager(str(self.db_path))
        self.llm_repo: LLMRequestRepository | None = None

        logger.info(f"LLM database manager initialized: {self.db_path}")

    def _get_default_db_path(self) -> str:
        """Get the default database path for LLM requests."""
        # Check if we're in test environment
        if "PYTEST_CURRENT_TEST" in os.environ:
            # Use temporary directory for tests
            import tempfile

            temp_dir = Path(tempfile.gettempdir()) / "theark_test"
            temp_dir.mkdir(exist_ok=True)
            return str(temp_dir / "llm_requests.db")

        # Use ./db directory for dev and prod (same as main database)
        project_root = Path(__file__).parent.parent.parent
        db_dir = project_root / "db"

        return str(db_dir / "llm_requests.db")

    def _ensure_directory_exists(self) -> None:
        """Ensure the database directory exists."""
        self.db_path.parent.mkdir(parents=True, exist_ok=True)

    async def __aenter__(self) -> "LLMDatabaseManager":
        """Async context manager entry."""
        await self.start()
        return self

    async def __aexit__(
        self,
        exc_type: type[BaseException] | None,
        exc_val: BaseException | None,
        exc_tb: Any,
    ) -> None:
        """Async context manager exit."""
        await self.stop()

    def __enter__(self) -> "LLMDatabaseManager":
        """Context manager entry."""
        self.start_sync()
        return self

    def __exit__(
        self,
        exc_type: type[BaseException] | None,
        exc_val: BaseException | None,
        exc_tb: Any,
    ) -> None:
        """Context manager exit."""
        self.stop_sync()

    async def start(self) -> None:
        """Start the LLM database manager (async)."""
        self.start_sync()

    def start_sync(self) -> None:
        """Start the LLM database manager (sync)."""
        # Connect to database
        self.db_manager.connect()

        # Initialize repository
        self.llm_repo = LLMRequestRepository(self.db_manager)

        # Create tables
        self.llm_repo.create_table()

        logger.info("LLM database manager started")

    async def stop(self) -> None:
        """Stop the LLM database manager (async)."""
        self.stop_sync()

    def stop_sync(self) -> None:
        """Stop the LLM database manager (sync)."""
        # Clean up resources if needed
        logger.info("LLM database manager stopped")

    @property
    def repository(self) -> LLMRequestRepository:
        """Get the LLM request repository."""
        if self.llm_repo is None:
            raise RuntimeError("LLM database manager not started")
        return self.llm_repo


# Global instance for easy access
_llm_db_manager: LLMDatabaseManager | None = None


def get_llm_db_manager() -> LLMDatabaseManager:
    """Get the global LLM database manager instance."""
    global _llm_db_manager
    if _llm_db_manager is None:
        _llm_db_manager = LLMDatabaseManager()
        _llm_db_manager.start_sync()
    return _llm_db_manager


def close_llm_db_manager() -> None:
    """Close the global LLM database manager."""
    global _llm_db_manager
    if _llm_db_manager is not None:
        _llm_db_manager.stop_sync()
        _llm_db_manager = None
