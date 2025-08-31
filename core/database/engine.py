"""Database engine factory for SQLModel."""

from pathlib import Path

from sqlalchemy.engine import Engine
from sqlmodel import SQLModel, create_engine

from core.log import get_logger
from core.models.rows import (
    ArxivCrawlProgress,
    ArxivFailedPaper,
    BatchItem,
    CrawlEvent,
    CrawlExecutionState,
    FeedItem,
    LLMBatchRequest,
    LLMRequest,
    Paper,
    Summary,
    SummaryRead,
    User,
    UserInterest,
    UserStar,
)
from core.types import Environment

logger = get_logger(__name__)


def setup_database_url(environment: Environment, db_path: Path | None = None) -> str:
    """Construct database URL based on environment configuration.

    Args:
        environment: Environment type
        db_path: Optional custom database path. If provided, overrides default path.

    Returns:
        Database connection URL
    """

    if environment == Environment.TESTING:
        return "sqlite:///:memory:"

    if db_path is not None:
        # Use custom path if provided
        db_path = Path(db_path)
    else:
        # Use default paths based on environment
        if environment == Environment.PRODUCTION:
            db_path = Path("db", "theark.db")
        elif environment == Environment.DEVELOPMENT:
            db_path = Path("db", "theark.dev.db")
        else:
            raise ValueError(f"Unknown environment: {environment}")

    # Ensure the directory exists
    db_path.parent.mkdir(parents=True, exist_ok=True)
    return f"sqlite:///{db_path}"


def create_database_engine(
    environment: Environment,
    echo: bool = False,
    db_path: Path | None = None,
) -> Engine:
    """Create database engine based on environment configuration.

    Args:
        environment: Environment type
        echo: Enable SQL echo for debugging
        db_path: Optional custom database path. If provided, overrides default path.

    Returns:
        Configured SQLModel engine
    """
    # Create SQLite URL
    database_url = setup_database_url(environment, db_path)
    logger.info(f"Creating database engine for: {database_url}")

    # Create engine with SQLite-specific configuration
    engine = create_engine(
        database_url,
        echo=echo,
        connect_args={
            "check_same_thread": False,
            "timeout": 60.0,
        },
        pool_pre_ping=True,
        pool_recycle=3600,
        pool_size=10,
    )
    return engine


def create_database_tables(engine: Engine) -> None:
    """Create all database tables using SQLModel."""
    # Import models here to avoid circular imports

    logger.info("Creating database tables...")

    # Create all tables defined in SQLModel models
    SQLModel.metadata.create_all(engine)

    row_models = [
        ArxivCrawlProgress,
        ArxivFailedPaper,
        CrawlExecutionState,
        Paper,
        Summary,
        SummaryRead,
        User,
        UserInterest,
        UserStar,
        FeedItem,
        CrawlEvent,
        LLMRequest,
        LLMBatchRequest,
        BatchItem,
    ]
    for model in row_models:
        logger.info(f"> Created table for {model.__tablename__}")


def drop_database_tables(engine: Engine) -> None:
    """Drop all database tables (use with caution)."""
    logger.warning("Dropping all database tables...")

    # Drop all tables defined in SQLModel models
    SQLModel.metadata.drop_all(engine)

    logger.info("Database tables dropped successfully")


def reset_database(engine: Engine) -> None:
    """Reset database by dropping and recreating all tables."""
    logger.warning("Resetting database...")

    drop_database_tables(engine)
    create_database_tables(engine)

    logger.info("Database reset completed")
