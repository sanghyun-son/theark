"""FastAPI dependencies for SQLModel integration."""

from collections.abc import Generator
from typing import Annotated

from fastapi import Depends, Request
from sqlalchemy.engine import Engine
from sqlmodel import Session

from core.batch.background_manager import BackgroundBatchManager
from core.config import Settings
from core.database.repository import (
    PaperRepository,
    SummaryRepository,
    UserInterestRepository,
    UserRepository,
    UserStarRepository,
)
from core.extractors.concrete.arxiv_source_explorer import ArxivSourceExplorer
from core.llm.openai_client import UnifiedOpenAIClient
from core.log import get_logger
from core.models.rows import User
from core.services.crawl_service import CrawlService

logger = get_logger(__name__)


def get_settings(request: Request) -> Settings:
    """Get settings from app state."""
    settings: Settings = request.app.state.settings
    return settings


# Database engine dependency
def get_engine(request: Request) -> Engine:
    """Get database engine from app state."""
    engine: Engine = request.app.state.engine
    return engine


# Database session dependency
def get_db(
    engine: Annotated[Engine, Depends(get_engine)],
) -> Generator[Session, None, None]:
    """Get database session from app state."""
    with Session(engine) as session:
        yield session


# Repository dependencies
def get_paper_repository(db: Annotated[Session, Depends(get_db)]) -> PaperRepository:
    """Get paper repository."""
    return PaperRepository(db)


def get_summary_repository(
    db: Annotated[Session, Depends(get_db)],
) -> SummaryRepository:
    """Get summary repository."""
    return SummaryRepository(db)


def get_user_repository(db: Annotated[Session, Depends(get_db)]) -> UserRepository:
    """Get user repository."""
    return UserRepository(db)


def get_user_interest_repository(
    db: Annotated[Session, Depends(get_db)],
) -> UserInterestRepository:
    """Get user interest repository."""
    return UserInterestRepository(db)


def get_user_star_repository(
    db: Annotated[Session, Depends(get_db)],
) -> UserStarRepository:
    """Get user star repository."""
    return UserStarRepository(db)


# Service dependencies
def get_openai_client(request: Request) -> UnifiedOpenAIClient:
    """Get OpenAI client from app state."""
    client: UnifiedOpenAIClient = request.app.state.summary_client
    return client


def get_background_batch_manager(request: Request) -> BackgroundBatchManager:
    """Get background batch manager from app state."""
    manager: BackgroundBatchManager = request.app.state.background_batch_manager
    return manager


# User authentication dependency
def get_current_user(
    request: Request,
    user_repo: Annotated[UserRepository, Depends(get_user_repository)],
) -> User:
    """Get current user (simplified for now)."""
    # For now, return a default user
    # In a real application, this would extract user info from JWT token
    DEFAULT_USER_ID = 1
    user = user_repo.get_by_id(DEFAULT_USER_ID)
    if not user:
        user = User(
            user_id=DEFAULT_USER_ID,
            email="default@example.com",
            display_name="default_user",
        )
        user = user_repo.create(user)

    return user


# Summary generator dependency
def get_summary_generator(request: Request) -> UnifiedOpenAIClient:
    """Get summary generator client."""
    client: UnifiedOpenAIClient = request.app.state.summary_client
    return client


# Crawler dependencies
def get_crawl_service(request: Request) -> CrawlService:
    """Get crawl service from app state."""
    service: CrawlService = request.app.state.crawl_service
    return service


def get_arxiv_explorer(request: Request) -> ArxivSourceExplorer:
    """Get ArXiv explorer from app state."""
    explorer: ArxivSourceExplorer = request.app.state.arxiv_explorer
    return explorer
