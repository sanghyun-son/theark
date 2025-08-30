"""Comprehensive tests for PaperService."""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from sqlmodel import Session

from core.database.repository import (
    PaperRepository,
    SummaryReadRepository,
    SummaryRepository,
    UserRepository,
    UserStarRepository,
)
from core.extractors import ArxivExtractor
from core.extractors.factory import extractor_factory
from core.llm.openai_client import UnifiedOpenAIClient
from core.models import PaperCreateRequest
from core.models.api.responses import (
    PaperDeleteResponse,
    StarredPapersResponse,
    StarResponse,
    SummaryReadResponse,
)
from core.models.rows import Paper, Summary, SummaryRead, User, UserStar
from core.services.paper_service import PaperService
from core.types import PaperSummaryStatus

# =============================================================================
# CRUD Operations Tests
# =============================================================================


@pytest.mark.asyncio
async def test_create_paper_success(
    paper_service: PaperService,
    mock_db_session: Session,
    mock_openai_client: UnifiedOpenAIClient,
    mock_arxiv_extractor: ArxivExtractor,
) -> None:
    """Test successful paper creation."""
    # Register the mock extractor

    extractor_factory.register_extractor("arxiv", mock_arxiv_extractor)
    paper_data = PaperCreateRequest(
        url="https://arxiv.org/abs/1706.03762",
        skip_auto_summarization=True,
        summary_language="English",
    )

    paper_repo = PaperRepository(mock_db_session)
    result = await paper_service.create_paper(
        paper_data,
        paper_repo,
        mock_openai_client,
        skip_auto_summarization=True,
    )

    assert result.is_starred is False
    assert result.is_read is False
    assert result.summary is None


@pytest.mark.asyncio
async def test_get_paper_by_id_success(
    paper_service: PaperService,
    saved_paper: Paper,
    mock_db_session: Session,
) -> None:

    result = await paper_service.get_paper("1", mock_db_session, user_id=1)

    assert result.paper_id == saved_paper.paper_id
    assert result.arxiv_id == saved_paper.arxiv_id
    assert result.title == saved_paper.title


@pytest.mark.asyncio
async def test_get_paper_with_star_and_read_status(
    paper_service: PaperService,
    saved_paper: Paper,
    saved_summary: Summary,
    saved_user: User,
    user_star_repo: UserStarRepository,
    summary_read_repo: SummaryReadRepository,
    mock_db_session: Session,
) -> None:
    """Test getting paper with star and read status from database."""

    assert saved_user.user_id is not None
    assert saved_paper.paper_id is not None
    user_star_repo.add_user_star(saved_user.user_id, saved_paper.paper_id)
    summary_read_repo.mark_as_read(saved_user.user_id, saved_paper.paper_id)
    result = await paper_service.get_paper(
        saved_paper.arxiv_id,
        mock_db_session,
        user_id=saved_user.user_id,
    )

    # Check that the result is a PaperResponse with correct fields
    assert result.paper_id == saved_paper.paper_id
    assert result.arxiv_id == saved_paper.arxiv_id
    assert result.title == saved_paper.title
    assert result.is_starred is True  # User has starred this paper
    assert result.is_read is True  # User has read the summary


@pytest.mark.asyncio
async def test_get_paper_by_arxiv_id_success(
    paper_service: PaperService,
    saved_paper: Paper,
    mock_db_session: Session,
) -> None:

    result = await paper_service.get_paper(
        saved_paper.arxiv_id,
        mock_db_session,
        user_id=1,
    )

    # Check that the result is a PaperResponse with correct fields
    assert result.paper_id == saved_paper.paper_id
    assert result.arxiv_id == saved_paper.arxiv_id
    assert result.title == saved_paper.title


@pytest.mark.asyncio
async def test_delete_paper_success(
    paper_service: PaperService,
    saved_paper: Paper,
    mock_db_session: Session,
) -> None:
    """Test successful paper deletion."""

    result = paper_service.delete_paper(
        saved_paper.arxiv_id,
        mock_db_session,
    )

    assert result.success
    assert "deleted successfully" in result.message


@pytest.mark.asyncio
async def test_delete_paper_not_found(
    paper_service: PaperService,
    mock_db_session: Session,
) -> None:

    with pytest.raises(ValueError, match="Paper not found"):
        await paper_service.delete_paper("999", mock_db_session)


@pytest.mark.asyncio
async def test_get_papers(
    paper_service: PaperService,
    saved_user: User,
    saved_papers: list[Paper],
    mock_db_session: Session,
) -> None:
    """Test getting papers with summaries."""

    result = await paper_service.get_papers(
        mock_db_session,
        user_id=saved_user.user_id,
        skip=0,
        limit=10,
        language="English",
    )
    assert len(result.papers) == len(saved_papers)


# =============================================================================
# Star Operations Tests
# =============================================================================


def test_add_star_success(
    paper_service: PaperService,
    saved_paper: Paper,
    saved_user: User,
    mock_db_session: Session,
) -> None:
    """Test successful star addition."""
    response = paper_service.add_star(
        mock_db_session,
        saved_user.user_id,
        saved_paper.paper_id,
        note="Interesting paper",
    )
    assert response.success
    assert response.is_starred


def test_add_star_paper_not_found(
    paper_service: PaperService,
    saved_user: User,
    mock_db_session: Session,
) -> None:
    """Test star addition with non-existent paper."""
    with pytest.raises(ValueError, match="not found"):
        paper_service.add_star(
            mock_db_session,
            saved_user.user_id,
            999,
        )


def test_add_star_user_not_found(
    paper_service: PaperService,
    saved_paper: Paper,
    mock_db_session: Session,
) -> None:
    """Test star addition with non-existent user."""
    with pytest.raises(ValueError, match="not found"):
        response = paper_service.add_star(
            mock_db_session,
            999,
            saved_paper.paper_id,
        )


def test_remove_star_success(
    paper_service: PaperService,
    saved_paper: Paper,
    saved_user: User,
    mock_db_session: Session,
) -> None:
    """Test successful star removal."""
    # First add a star
    paper_service.add_star(
        mock_db_session,
        saved_user.user_id,
        saved_paper.paper_id,
        note="Interesting paper",
    )

    # Then remove it
    response = paper_service.remove_star(
        mock_db_session,
        saved_user.user_id,
        saved_paper.paper_id,
    )
    assert response.success
    assert not response.is_starred
    assert "unstarred" in response.message


def test_remove_star_paper_not_found(
    paper_service: PaperService,
    saved_user: User,
    mock_db_session: Session,
) -> None:
    """Test star removal with non-existent paper."""
    with pytest.raises(ValueError, match="not found"):
        paper_service.remove_star(
            mock_db_session,
            saved_user.user_id,
            999,
        )


def test_remove_star_user_not_found(
    paper_service: PaperService,
    saved_paper: Paper,
    mock_db_session: Session,
) -> None:
    """Test star removal with non-existent user."""
    with pytest.raises(ValueError, match="not found"):
        paper_service.remove_star(
            mock_db_session,
            999,
            saved_paper.paper_id,
        )


@pytest.mark.asyncio
async def test_get_starred_papers_success(
    paper_service: PaperService,
    saved_papers: list[Paper],
    saved_user: User,
    mock_db_session: Session,
) -> None:
    """Test getting starred papers for a user."""
    # Create a user star repository and add some stars
    assert saved_user.user_id is not None
    user_star_repo = UserStarRepository(mock_db_session)

    # Star the first two papers
    for paper in saved_papers[:2]:
        if paper.paper_id is not None:
            user_star_repo.add_user_star(saved_user.user_id, paper.paper_id)

    result = await paper_service.get_starred_papers(
        saved_user.user_id,
        mock_db_session,
        skip=0,
        limit=10,
    )
    assert isinstance(result, StarredPapersResponse)
    assert len(result.papers) == 2  # Should have 2 starred papers


# =============================================================================
# Summary Operations Tests
# =============================================================================


@pytest.mark.asyncio
async def test_mark_summary_as_read_success(
    paper_service: PaperService,
    saved_paper: Paper,
    saved_user: User,
    saved_summary: Summary,
    mock_db_session: Session,
) -> None:
    """Test successful summary read marking."""
    assert saved_user.user_id is not None
    result = await paper_service.mark_summary_as_read(
        str(saved_paper.paper_id),
        saved_user.user_id,
        mock_db_session,
        language="English",
    )

    assert result.success
    assert "marked as read" in result.message


@pytest.mark.asyncio
async def test_mark_summary_as_read_paper_not_found(
    paper_service: PaperService,
    saved_user: User,
    mock_db_session: Session,
) -> None:
    """Test marking summary as read when paper not found."""
    assert saved_user.user_id is not None
    with pytest.raises(ValueError, match="Paper not found"):
        await paper_service.mark_summary_as_read(
            "999",
            saved_user.user_id,
            mock_db_session,
            language="English",
        )


@pytest.mark.asyncio
async def test_mark_summary_as_read_summary_not_found(
    paper_service: PaperService,
    saved_paper: Paper,
    saved_user: User,
    mock_db_session: Session,
) -> None:
    """Test marking summary as read when summary not found."""
    assert saved_user.user_id is not None
    with pytest.raises(ValueError, match="Summary not found"):
        await paper_service.mark_summary_as_read(
            str(saved_paper.paper_id),
            saved_user.user_id,
            mock_db_session,
            language="Korean",  # Different language, no summary exists
        )


@pytest.mark.asyncio
async def test_mark_summary_as_read_failed(
    paper_service: PaperService,
    saved_paper: Paper,
    saved_user: User,
    mock_db_session: Session,
) -> None:
    """Test marking summary as read when operation fails."""
    assert saved_user.user_id is not None
    with pytest.raises(ValueError, match="Summary not found"):
        await paper_service.mark_summary_as_read(
            str(saved_paper.paper_id),
            saved_user.user_id,
            mock_db_session,
            language="Korean",  # Different language, no summary exists
        )


# =============================================================================
# Internal Methods Tests
# =============================================================================


@pytest.mark.asyncio
async def test_get_paper_by_identifier_by_id(
    paper_service: PaperService,
    saved_paper: Paper,
    mock_db_session: Session,
) -> None:
    """Test getting paper by ID using internal method."""
    assert saved_paper.paper_id is not None
    result = paper_service._get_paper_by_identifier(
        saved_paper.arxiv_id,
        mock_db_session,
    )

    assert result is not None
    assert result.paper_id == saved_paper.paper_id
    assert result.arxiv_id == saved_paper.arxiv_id


@pytest.mark.asyncio
async def test_get_paper_by_identifier_by_arxiv_id(
    paper_service: PaperService,
    saved_paper: Paper,
    mock_db_session: Session,
) -> None:
    """Test getting paper by arXiv ID using internal method."""
    # Test getting paper by arXiv ID using the internal method
    result = paper_service._get_paper_by_identifier(
        saved_paper.arxiv_id,
        mock_db_session,
    )

    assert result is not None
    assert result.paper_id == saved_paper.paper_id
    assert result.arxiv_id == saved_paper.arxiv_id


@pytest.mark.asyncio
async def test_get_paper_by_identifier_not_found(
    paper_service: PaperService,
    mock_db_session: Session,
) -> None:
    """Test getting paper by identifier when not found."""
    paper_repo = PaperRepository(mock_db_session)

    with (
        patch.object(paper_repo, "get_by_id", return_value=None),
        patch.object(paper_repo, "get_by_arxiv_id", return_value=None),
    ):

        result = paper_service._get_paper_by_identifier("999", mock_db_session)

        assert result is None


def test_check_valid_user_and_paper_success(
    paper_service: PaperService,
    saved_paper: Paper,
    saved_user: User,
    mock_db_session: Session,
) -> None:
    """Test successful user and paper validation."""
    user_repo = UserRepository(mock_db_session)
    paper_repo = PaperRepository(mock_db_session)

    with (
        patch.object(user_repo, "get_by_id", return_value=saved_user),
        patch.object(paper_repo, "get_by_id", return_value=saved_paper),
    ):

        result = paper_service._check_valid_user_and_paper(
            mock_db_session,
            saved_user.user_id,
            saved_paper.paper_id,
        )

        assert result == ""


def test_check_valid_user_and_paper_user_not_found(
    paper_service: PaperService,
    saved_paper: Paper,
    mock_db_session: Session,
) -> None:
    """Test user and paper validation when user not found."""
    user_repo = UserRepository(mock_db_session)
    paper_repo = PaperRepository(mock_db_session)

    with (
        patch.object(user_repo, "get_by_id", return_value=None),
        patch.object(paper_repo, "get_by_id", return_value=saved_paper),
    ):

        result = paper_service._check_valid_user_and_paper(
            mock_db_session,
            999,
            saved_paper.paper_id,
        )

        assert "User 999 not found" in result


def test_check_valid_user_and_paper_paper_not_found(
    paper_service: PaperService,
    saved_user: User,
    mock_db_session: Session,
) -> None:
    """Test user and paper validation when paper not found."""
    user_repo = UserRepository(mock_db_session)
    paper_repo = PaperRepository(mock_db_session)

    with (
        patch.object(user_repo, "get_by_id", return_value=saved_user),
        patch.object(paper_repo, "get_by_id", return_value=None),
    ):

        result = paper_service._check_valid_user_and_paper(
            mock_db_session,
            saved_user.user_id,
            999,
        )

        assert "Paper 999 not found" in result
