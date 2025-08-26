"""Shared test fixtures for SQLite database tests."""

from pathlib import Path

import pytest
import pytest_asyncio

from core.models.database.entities import PaperEntity
from core.database.implementations.sqlite.sqlite_manager import SQLiteManager
from core.database.repository import (
    CrawlEventRepository,
    FeedRepository,
    PaperRepository,
    SummaryRepository,
    UserRepository,
)


@pytest.fixture
def temp_db_path(tmp_path: Path) -> Path:
    """Create a temporary database path using pytest's tmp_path."""
    return tmp_path / "test.db"


@pytest_asyncio.fixture
async def db_manager(temp_db_path: Path) -> SQLiteManager:
    """Create a database manager with temporary database."""
    manager = SQLiteManager(temp_db_path)
    async with manager:
        await manager.create_tables()
        yield manager


@pytest.fixture
def paper_repo(db_manager: SQLiteManager) -> PaperRepository:
    """Create a paper repository with database manager."""
    return PaperRepository(db_manager)


@pytest.fixture
def summary_repo(db_manager: SQLiteManager) -> SummaryRepository:
    """Create a summary repository with database manager."""
    return SummaryRepository(db_manager)


@pytest.fixture
def user_repo(db_manager: SQLiteManager) -> UserRepository:
    """Create a user repository with database manager."""
    return UserRepository(db_manager)


@pytest.fixture
def feed_repo(db_manager: SQLiteManager) -> FeedRepository:
    """Create a feed repository with database manager."""
    return FeedRepository(db_manager)


@pytest.fixture
def event_repo(db_manager: SQLiteManager) -> CrawlEventRepository:
    """Create a crawl event repository with database manager."""
    return CrawlEventRepository(db_manager)


@pytest.fixture
def sample_paper() -> PaperEntity:
    """Create a sample paper for testing."""
    return PaperEntity(
        arxiv_id="2101.00001",
        title="Test Paper",
        abstract="This is a test abstract",
        primary_category="cs.CL",
        categories="cs.CL,cs.LG",
        authors="John Doe;Jane Smith",
        url_abs="https://arxiv.org/abs/2101.00001",
        url_pdf="https://arxiv.org/pdf/2101.00001",
        published_at="2021-01-01T00:00:00Z",
        updated_at="2021-01-01T00:00:00Z",
    )


@pytest.fixture
def sample_papers() -> list[PaperEntity]:
    """Create sample papers for testing."""
    return [
        PaperEntity(
            arxiv_id="2101.00001",
            title="Machine Learning Paper",
            abstract="This paper discusses machine learning techniques",
            primary_category="cs.AI",
            categories="cs.AI",
            authors="Author 1",
            url_abs="https://arxiv.org/abs/2101.00001",
            published_at="2021-01-01T00:00:00Z",
            updated_at="2021-01-01T00:00:00Z",
        ),
        PaperEntity(
            arxiv_id="2101.00002",
            title="Deep Learning Research",
            abstract="Deep learning applications in computer vision",
            primary_category="cs.AI",
            categories="cs.AI",
            authors="Author 2",
            url_abs="https://arxiv.org/abs/2101.00002",
            published_at="2021-01-01T00:00:00Z",
            updated_at="2021-01-01T00:00:00Z",
        ),
        PaperEntity(
            arxiv_id="2101.00003",
            title="Natural Language Processing",
            abstract="NLP techniques for text analysis",
            primary_category="cs.CL",
            categories="cs.CL",
            authors="Author 3",
            url_abs="https://arxiv.org/abs/2101.00003",
            published_at="2021-01-01T00:00:00Z",
            updated_at="2021-01-01T00:00:00Z",
        ),
    ]
