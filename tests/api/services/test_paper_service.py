"""Tests for PaperService star functionality."""

import pytest

from api.services.paper_service import PaperService
from core.models.database.entities import PaperEntity, UserEntity
from core.models.domain.user import User
from core.models.api.responses import StarResponse, StarredPapersResponse
from crawler.database import PaperRepository, UserRepository


@pytest.fixture
def paper_service() -> PaperService:
    """Create PaperService instance."""
    return PaperService()


@pytest.fixture
def sample_paper() -> PaperEntity:
    """Create sample paper entity."""
    return PaperEntity(
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
        updated_at="2021-01-01",
    )


@pytest.fixture
def sample_user() -> User:
    """Create sample user from domain model."""
    return User(
        user_id=1,
        email="default@theark.local",
        display_name="Default User",
    )


@pytest.mark.asyncio
async def test_add_star_success(
    paper_service: PaperService,
    sample_paper: PaperEntity,
    sample_user: User,
    mock_sqlite_db,
) -> None:
    """Test successful star addition."""
    # Create real repositories
    paper_repo = PaperRepository(mock_sqlite_db)
    user_repo = UserRepository(mock_sqlite_db)

    # Save the paper to the database
    paper_id = paper_repo.create(sample_paper)

    # Create the default user in the database
    default_user = UserEntity(
        user_id=1,
        email="default@theark.local",
        display_name="Default User",
    )
    user_repo.create_user(default_user)

    # Test
    result = await paper_service.add_star(
        paper_id, mock_sqlite_db, sample_user, note="Interesting paper"
    )

    # Assertions
    assert isinstance(result, StarResponse)
    assert result.success is True
    assert result.paper_id == paper_id
    assert result.is_starred is True
    assert result.note == "Interesting paper"
    assert "starred successfully" in result.message


@pytest.mark.asyncio
async def test_add_star_paper_not_found(
    paper_service: PaperService,
    sample_user: User,
    mock_sqlite_db,
) -> None:
    """Test star addition with non-existent paper."""
    with pytest.raises(ValueError, match="Paper 999 not found"):
        await paper_service.add_star(999, mock_sqlite_db, sample_user)


@pytest.mark.asyncio
async def test_remove_star_success(
    paper_service: PaperService,
    sample_paper: PaperEntity,
    sample_user: User,
    mock_sqlite_db,
) -> None:
    """Test successful star removal."""
    # Create real repositories
    paper_repo = PaperRepository(mock_sqlite_db)
    user_repo = UserRepository(mock_sqlite_db)

    # Save the paper to the database
    paper_id = paper_repo.create(sample_paper)

    # Create the default user in the database
    default_user = UserEntity(
        user_id=1,
        email="default@theark.local",
        display_name="Default User",
    )
    user_repo.create_user(default_user)

    # Add a star first
    await paper_service.add_star(
        paper_id, mock_sqlite_db, sample_user, note="Test note"
    )

    # Test removal
    result = await paper_service.remove_star(paper_id, mock_sqlite_db, sample_user)

    # Assertions
    assert isinstance(result, StarResponse)
    assert result.success is True
    assert result.paper_id == paper_id
    assert result.is_starred is False
    assert result.note is None
    assert "removed" in result.message


@pytest.mark.asyncio
async def test_remove_star_paper_not_found(
    paper_service: PaperService,
    sample_user: User,
    mock_sqlite_db,
) -> None:
    """Test star removal with non-existent paper."""
    with pytest.raises(ValueError, match="Paper 999 not found"):
        await paper_service.remove_star(999, mock_sqlite_db, sample_user)


@pytest.mark.asyncio
async def test_is_paper_starred_true(
    paper_service: PaperService,
    sample_paper: PaperEntity,
    sample_user: User,
    mock_sqlite_db,
) -> None:
    """Test checking if a paper is starred (when it is)."""
    # Create real repositories
    paper_repo = PaperRepository(mock_sqlite_db)
    user_repo = UserRepository(mock_sqlite_db)

    # Save the paper to the database
    paper_id = paper_repo.create(sample_paper)

    # Create the default user in the database
    default_user = UserEntity(
        user_id=1,
        email="default@theark.local",
        display_name="Default User",
    )
    user_repo.create_user(default_user)

    # Add a star
    await paper_service.add_star(
        paper_id, mock_sqlite_db, sample_user, note="Test note"
    )

    # Test checking star status
    result = await paper_service.is_paper_starred(paper_id, mock_sqlite_db, sample_user)

    # Assertions
    assert isinstance(result, StarResponse)
    assert result.success is True
    assert result.paper_id == paper_id
    assert result.is_starred is True
    assert result.note == "Test note"
    assert "is starred" in result.message


@pytest.mark.asyncio
async def test_is_paper_starred_false(
    paper_service: PaperService,
    sample_paper: PaperEntity,
    sample_user: User,
    mock_sqlite_db,
) -> None:
    """Test checking if a paper is starred (when it is not)."""
    # Create real repositories
    paper_repo = PaperRepository(mock_sqlite_db)
    user_repo = UserRepository(mock_sqlite_db)

    # Save the paper to the database
    paper_id = paper_repo.create(sample_paper)

    # Create the default user in the database
    default_user = UserEntity(
        user_id=1,
        email="default@theark.local",
        display_name="Default User",
    )
    user_repo.create_user(default_user)

    # Test checking star status (without adding a star)
    result = await paper_service.is_paper_starred(paper_id, mock_sqlite_db, sample_user)

    # Assertions
    assert isinstance(result, StarResponse)
    assert result.success is True
    assert result.paper_id == paper_id
    assert result.is_starred is False
    assert result.note is None
    assert "is not starred" in result.message
