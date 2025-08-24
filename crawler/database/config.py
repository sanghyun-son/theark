"""Database configuration for different environments."""

from pathlib import Path

from core.log import get_logger
from core.types import Environment

logger = get_logger(__name__)


class DatabaseConfig:
    """Database configuration manager."""

    def __init__(self, environment: Environment = Environment.DEVELOPMENT) -> None:
        """Initialize database configuration.

        Args:
            environment: Environment type (development, testing, production)
        """
        self.environment = environment
        self._base_dir = Path.cwd()

    @property
    def database_dir(self) -> Path:
        """Get database directory for current environment."""
        if self.environment == Environment.TESTING:
            # For testing, use a temporary directory
            return Path("/tmp")
        else:
            # For development and production, use ./db directory
            return self._base_dir / "db"

    @property
    def database_path(self) -> Path:
        """Get database file path for current environment."""
        db_dir = self.database_dir
        db_dir.mkdir(parents=True, exist_ok=True)

        if self.environment == Environment.TESTING:
            # For testing, use arxiv.test.db
            return db_dir / "arxiv.test.db"
        elif self.environment == Environment.DEVELOPMENT:
            # For development, use arxiv.dev.db
            return db_dir / "arxiv.dev.db"
        else:
            # For production, use arxiv.db
            return db_dir / "arxiv.db"

    def get_connection_string(self) -> str:
        """Get database connection string."""
        return str(self.database_path)

    def setup_database_directory(self) -> None:
        """Create database directory if it doesn't exist."""
        if self.environment != Environment.TESTING:
            self.database_dir.mkdir(parents=True, exist_ok=True)
            logger.info(f"Database directory: {self.database_dir}")

    def get_backup_path(self, backup_name: str | None = None) -> Path:
        """Get backup database path.

        Args:
            backup_name: Optional backup name, defaults to timestamp

        Returns:
            Backup file path
        """
        if backup_name is None:
            from datetime import datetime

            backup_name = f"backup_{datetime.now().strftime('%Y%m%d_%H%M%S')}.db"

        return self.database_dir / "backups" / backup_name

    def get_log_path(self) -> Path:
        """Get database log file path."""
        return self.database_dir / "database.log"


# Convenience functions
def get_database_path(environment: Environment = Environment.DEVELOPMENT) -> Path:
    """Get database path for the specified environment.

    Args:
        environment: Environment type

    Returns:
        Database file path
    """
    config = DatabaseConfig(environment)
    return config.database_path


def get_database_dir(environment: Environment = Environment.DEVELOPMENT) -> Path:
    """Get database directory for the specified environment.

    Args:
        environment: Environment type

    Returns:
        Database directory path
    """
    config = DatabaseConfig(environment)
    return config.database_dir


def get_llm_database_path(environment: Environment = Environment.DEVELOPMENT) -> Path:
    """Get LLM database path for the specified environment.

    Args:
        environment: Environment type

    Returns:
        LLM database file path
    """
    config = DatabaseConfig(environment)
    db_dir = config.database_dir
    db_dir.mkdir(parents=True, exist_ok=True)

    if environment == Environment.TESTING:
        # For testing, use llm_requests.test.db
        return db_dir / "llm_requests.test.db"
    elif environment == Environment.DEVELOPMENT:
        # For development, use llm_requests.dev.db
        return db_dir / "llm_requests.dev.db"
    else:
        # For production, use llm_requests.db
        return db_dir / "llm_requests.db"


def setup_database_environment(
    environment: Environment = Environment.DEVELOPMENT,
) -> DatabaseConfig:
    """Setup database environment and return configuration.

    Args:
        environment: Environment type

    Returns:
        Database configuration
    """
    config = DatabaseConfig(environment)
    config.setup_database_directory()
    return config


__all__ = [
    "Environment",
    "DatabaseConfig",
    "get_database_path",
    "get_database_dir",
    "get_llm_database_path",
    "setup_database_environment",
]
