"""Dependency injection for FastAPI application."""

from typing import Annotated, AsyncGenerator

from fastapi import Depends

from core import get_logger
from crawler.database import LLMDatabaseManager, get_llm_db_manager

logger = get_logger(__name__)


async def get_llm_database() -> AsyncGenerator[LLMDatabaseManager, None]:
    """Get LLM database manager dependency."""
    try:
        db_manager = get_llm_db_manager()
        yield db_manager
    except Exception as e:
        logger.error(f"Failed to get LLM database: {e}")
        raise
    finally:
        # Note: In a real application, you might want to manage this differently
        # For now, we'll keep the global instance alive
        pass


# Type alias for dependency injection
LLMDatabase = Annotated[LLMDatabaseManager, Depends(get_llm_database)]
