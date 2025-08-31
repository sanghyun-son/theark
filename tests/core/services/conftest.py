"""Tests for PaperService star functionality."""

from typing import Generator

import pytest
from sqlmodel import Session

from core.database.repository import PaperRepository, SummaryRepository, UserRepository
from core.models.rows import Paper, User
from core.services.paper_service import PaperService
from core.services.star_service import StarService


@pytest.fixture
def paper_service() -> PaperService:
    """Create PaperService instance."""
    return PaperService()


@pytest.fixture
def star_service() -> StarService:
    """Create StarService instance."""
    return StarService()


@pytest.fixture
def sample_paper() -> Paper:
    """Create sample paper entity."""
    return Paper(
        paper_id=1,
        arxiv_id="2101.00001",
        latest_version=1,
        title="Test Paper",
        abstract="Test abstract",
        primary_category="cs.CL",
        categories="cs.CL, cs.AI",
        authors="John Doe, Jane Smith",
        url_abs="https://arxiv.org/abs/2101.00001",
        url_pdf="https://arxiv.org/pdf/2101.00001",
        published_at="2021-01-01",
    )


@pytest.fixture
def paper_repo(mock_db_session: Session) -> PaperRepository:
    """Create paper repository instance."""
    return PaperRepository(mock_db_session)


@pytest.fixture(scope="function")
def saved_paper(
    sample_paper: Paper,
    mock_db_session: Session,
) -> Generator[Paper, None, None]:
    """Create and save a paper to the database."""
    paper_repo = PaperRepository(mock_db_session)
    paper = paper_repo.create(sample_paper)
    yield paper


@pytest.fixture
def sample_user() -> User:
    """Create sample user from domain model."""
    return User(
        user_id=1,
        email="default@theark.local",
        display_name="Default User",
    )


@pytest.fixture(scope="function")
def saved_user(
    sample_user: User,
    mock_db_session: Session,
) -> Generator[User, None, None]:
    """Create and save a paper to the database."""
    user_repo = UserRepository(mock_db_session)
    user = user_repo.create(sample_user)
    yield user
