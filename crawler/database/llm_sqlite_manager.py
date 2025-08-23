"""Shared LLM request database manager."""

from pathlib import Path
from typing import Any

from core import get_logger
from core.database import BaseSQLiteManager

from .llm_repository import LLMRequestRepository

logger = get_logger(__name__)


class LLMSQLiteManager(BaseSQLiteManager):
    """SQLite-based database manager for LLM request tracking."""

    def __init__(self, db_path: str | Path):
        """Initialize LLM database manager.

        Args:
            db_path: Path to database file
        """
        super().__init__(db_path)
        self.llm_repo: LLMRequestRepository | None = None
        logger.info(f"LLM database manager initialized: {self.db_path}")

    def connect(self) -> None:
        """Connect to the LLM database."""
        super().connect()
        self.llm_repo = LLMRequestRepository(self)
        self.llm_repo.create_table()
        logger.info("LLM database connected")

    def disconnect(self) -> None:
        """Disconnect from the LLM database."""
        super().disconnect()
        self.llm_repo = None
        logger.info("LLM database disconnected")

    def create_tables(self) -> None:
        """Create all necessary tables."""
        if self.llm_repo:
            self.llm_repo.create_table()

    @property
    def repository(self) -> LLMRequestRepository:
        """Get the LLM request repository."""
        if self.llm_repo is None:
            raise RuntimeError("LLM database not connected")
        return self.llm_repo

    def __enter__(self) -> "LLMSQLiteManager":
        """Context manager entry."""
        self.connect()
        return self

    def __exit__(
        self,
        exc_type: type[BaseException] | None,
        exc_val: BaseException | None,
        exc_tb: Any,
    ) -> None:
        """Context manager exit."""
        self.disconnect()
