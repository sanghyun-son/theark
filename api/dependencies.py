"""Dependency injection container and dependencies."""

from typing import Annotated

from fastapi import Depends, Request

from api.services.paper_service import PaperService
from core import get_logger
from core.config import load_settings
from core.database.interfaces import DatabaseManager
from core.database.repository import UserRepository
from core.models.database.entities import UserEntity
from core.models.domain.user import DEFAULT_USER_ID, User
from crawler.arxiv.client import ArxivClient
from crawler.summarizer.openai_summarizer import OpenAISummarizer

logger = get_logger(__name__)
settings = load_settings()


def get_paper_service(request: Request) -> PaperService:
    """Get paper service from app state."""
    return request.app.state.paper_service  # type: ignore


async def get_current_user(request: Request) -> User:
    """Get current user information.

    Currently returns a default user. This will be replaced with actual
    authentication when user system is implemented.
    """
    # Get database manager from app state
    db_manager = request.app.state.db_manager

    # Create user repository and ensure default user exists
    user_repository = UserRepository(db_manager)
    user = await user_repository.get_user_by_id(DEFAULT_USER_ID)

    if user is None:
        # Create default user if it doesn't exist
        user_entity = UserEntity(
            user_id=DEFAULT_USER_ID,
            email="default@theark.local",
            display_name="Default User",
        )
        await user_repository.create_user(user_entity)
        user = user_entity

    return User(
        user_id=user.user_id,
        email=user.email,
        display_name=user.display_name,
    )


def get_arxiv_client(request: Request) -> ArxivClient:
    """Get ArxivClient instance from app state."""
    return request.app.state.arxiv_client  # type: ignore


def get_summary_client(request: Request) -> OpenAISummarizer:
    """Get SummaryClient instance from app state."""
    return request.app.state.summary_client  # type: ignore


def get_db_manager(request: Request) -> DatabaseManager:
    """Get database manager from app state."""
    return request.app.state.db_manager  # type: ignore


CurrentUser = Annotated[User, Depends(get_current_user)]
ArxivClientDep = Annotated[ArxivClient, Depends(get_arxiv_client)]
SummaryClientDep = Annotated[OpenAISummarizer, Depends(get_summary_client)]
DBManager = Annotated[DatabaseManager, Depends(get_db_manager)]
PaperServiceDep = Annotated[PaperService, Depends(get_paper_service)]
