"""Dependency injection container and dependencies."""

from typing import Annotated

from fastapi import Depends, Request

from api.services.paper_service import PaperService
from core import get_logger
from crawler.database import LLMSQLiteManager
from crawler.database.sqlite_manager import SQLiteManager

logger = get_logger(__name__)


def get_db_manager(request: Request) -> SQLiteManager:
    """Get database manager from app state."""
    return request.app.state.db_manager  # type: ignore


def get_llm_db_manager(request: Request) -> LLMSQLiteManager:
    """Get LLM database manager from app state."""
    return request.app.state.llm_db_manager  # type: ignore


def get_paper_service(request: Request) -> PaperService:
    """Get paper service from app state."""
    return request.app.state.paper_service  # type: ignore


# Type aliases for dependency injection
DBManager = Annotated[SQLiteManager, Depends(get_db_manager)]
LLMDBManager = Annotated[LLMSQLiteManager, Depends(get_llm_db_manager)]
PaperServiceDep = Annotated[PaperService, Depends(get_paper_service)]
