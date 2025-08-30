"""Tests for paper creation service."""

from unittest.mock import AsyncMock, patch

import pytest
from sqlmodel import Session

from core.database.repository.paper import PaperRepository
from core.extractors import extractor_factory
from core.extractors.concrete import ArxivExtractor
from core.models import PaperCreateRequest
from core.models.rows import Paper
from core.services.paper_creation_service import PaperCreationService


def test_extract_arxiv_id_from_request():
    """Test extracting arXiv ID from request."""
    extractor_factory.register_extractor("arxiv", ArxivExtractor())

    service = PaperCreationService()
    paper_data = PaperCreateRequest(url="https://arxiv.org/abs/2508.01234")
    arxiv_id = service._extract_arxiv_id(paper_data)
    assert arxiv_id == "2508.01234"


def test_extract_arxiv_id_error_no_identifier():
    """Test error when no identifier is provided."""
    service = PaperCreationService()

    # Create a PaperCreate with empty URL to test the error case
    paper_data = PaperCreateRequest(url="")
    with pytest.raises(ValueError, match="No URL provided"):
        service._extract_arxiv_id(paper_data)


@pytest.mark.asyncio
async def test_create_paper_new_paper(
    mock_db_session: Session,
    paper_repo: PaperRepository,
    mock_arxiv_extractor: ArxivExtractor,
) -> None:
    """Test creating a new paper."""
    # Setup extractor for test
    extractor_factory.register_extractor("arxiv", mock_arxiv_extractor)

    paper_creation_service = PaperCreationService()
    paper_data = PaperCreateRequest(
        url="https://arxiv.org/abs/1706.03762"
    )  # Use predefined paper ID

    # Act
    result = await paper_creation_service.create_paper(paper_data, paper_repo)

    # Assert
    assert isinstance(result, Paper)
    assert result.arxiv_id == "1706.03762"
    assert result.title == "Attention Is All You Need"  # Expected title from mock data

    # Verify paper was saved to database
    saved_paper = paper_repo.get_by_arxiv_id("1706.03762")
    assert saved_paper is not None
    assert saved_paper.arxiv_id == "1706.03762"


@pytest.mark.asyncio
async def test_create_paper_existing_paper(
    saved_paper: Paper,
    mock_db_session: Session,
    mock_arxiv_extractor: ArxivExtractor,
) -> None:
    """Test creating paper when it already exists."""
    extractor_factory.register_extractor("arxiv", mock_arxiv_extractor)

    paper_creation_service = PaperCreationService()
    paper_data = PaperCreateRequest(url=f"https://arxiv.org/abs/{saved_paper.arxiv_id}")

    # Create paper repository from session
    paper_repo = PaperRepository(mock_db_session)

    result = await paper_creation_service.create_paper(
        paper_data,
        paper_repo,
    )

    assert isinstance(result, Paper)
    assert result.arxiv_id == saved_paper.arxiv_id
    assert result.paper_id == saved_paper.paper_id


@pytest.mark.asyncio
async def test_get_paper_by_identifier_arxiv_id(
    saved_paper: Paper,
    mock_db_session: Session,
) -> None:
    """Test getting paper by arXiv ID."""
    paper_creation_service = PaperCreationService()

    result = await paper_creation_service.get_paper_by_identifier(
        saved_paper.arxiv_id, mock_db_session
    )

    assert result is not None
    assert result.arxiv_id == saved_paper.arxiv_id
    assert result.paper_id == saved_paper.paper_id


@pytest.mark.asyncio
async def test_get_paper_by_identifier_paper_id(
    saved_paper: Paper,
    mock_db_session: Session,
) -> None:
    """Test getting paper by paper ID."""
    paper_creation_service = PaperCreationService()

    # Act
    result = await paper_creation_service.get_paper_by_identifier(
        str(saved_paper.paper_id), mock_db_session
    )

    # Assert
    assert result is not None
    assert result.paper_id == saved_paper.paper_id
    assert result.arxiv_id == saved_paper.arxiv_id


@pytest.mark.asyncio
async def test_get_paper_by_identifier_not_found(
    mock_db_session: Session,
) -> None:
    """Test getting paper by identifier when not found."""
    paper_creation_service = PaperCreationService()

    # Act
    result = await paper_creation_service.get_paper_by_identifier(
        "nonexistent",
        mock_db_session,
    )

    # Assert
    assert result is None
