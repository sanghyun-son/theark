"""Dependency injection container and dependencies."""

from typing import Annotated

from fastapi import Depends, HTTPException, Request

from core import get_logger
from core.batch.background_manager import BackgroundBatchManager
from core.config import load_settings
from core.database.interfaces import DatabaseManager
from core.database.repository import UserRepository
from core.llm.applications.summary import SummaryGenerator
from core.llm.openai_client import UnifiedOpenAIClient
from core.models.database.entities import UserEntity
from core.models.domain.user import DEFAULT_USER_ID, User

logger = get_logger(__name__)
settings = load_settings()


async def get_current_user(request: Request) -> User:
    """Get current user information.

    Currently returns a default user. This will be replaced with actual
    authentication when user system is implemented.
    """
    # Create user repository and ensure default user exists
    db_manager = get_db_manager(request)
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
        logger.info(f"Created a default user: {user}")

    return User(
        user_id=user.user_id,
        email=user.email,
        display_name=user.display_name,
    )


def get_db_manager(request: Request) -> DatabaseManager:
    """Get database manager from app state."""
    return request.app.state.db_manager  # type: ignore


def get_batch_manager(request: Request) -> BackgroundBatchManager:
    """Get background batch manager from app state."""
    if not hasattr(request.app.state, "background_batch_manager"):
        raise HTTPException(
            status_code=503, detail="Background batch manager not available"
        )
    return request.app.state.background_batch_manager  # type: ignore


def get_summary_client(request: Request) -> UnifiedOpenAIClient:
    """Get OpenAI summary client from app state."""
    if not hasattr(request.app.state, "summary_client"):
        raise HTTPException(
            status_code=503, detail="OpenAI summary client not available"
        )
    return request.app.state.summary_client  # type: ignore


def get_summary_generator(request: Request) -> SummaryGenerator:
    """Get SummaryGenerator from app state."""
    if not hasattr(request.app.state, "summary_client"):
        raise HTTPException(status_code=503, detail="OpenAI client not available")
    # Create SummaryGenerator on demand
    return SummaryGenerator()


def get_summary_generator_dep(request: Request) -> SummaryGenerator:
    """Get SummaryGenerator dependency for API endpoints."""
    return get_summary_generator(request)


CurrentUser = Annotated[User, Depends(get_current_user)]
SummaryClientDep = Annotated[UnifiedOpenAIClient, Depends(get_summary_client)]
SummaryGeneratorDep = Annotated[SummaryGenerator, Depends(get_summary_generator_dep)]
DBManager = Annotated[DatabaseManager, Depends(get_db_manager)]
BatchManager = Annotated[BackgroundBatchManager, Depends(get_batch_manager)]
OpenAIBatchClientDep = Annotated[UnifiedOpenAIClient, Depends(get_summary_client)]
