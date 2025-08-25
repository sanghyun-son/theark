"""Tests for paper summarization service."""

import pytest

from api.services.paper_summarization_service import PaperSummarizationService
from core.models.database.entities import PaperEntity, SummaryEntity
from core.database.llm_sqlite_manager import LLMSQLiteManager
from core.database.sqlite_manager import SQLiteManager
from core.database.repository import PaperRepository
from crawler.summarizer.client import SummaryClient


@pytest.fixture
def mock_paper() -> PaperEntity:
    """Create a mock PaperEntity for testing."""
    return PaperEntity(
        paper_id=None,
        arxiv_id="2508.01234",
        title="Test Paper Title",
        abstract="Test paper abstract",
        primary_category="cs.AI",
        categories="cs.AI,cs.LG",
        authors="Author One;Author Two",
        url_abs="https://arxiv.org/abs/2508.01234",
        url_pdf="https://arxiv.org/pdf/2508.01234",
        published_at="2023-08-01T00:00:00Z",
        updated_at="2023-08-01T00:00:00Z",
    )


@pytest.fixture
def saved_paper(mock_paper: PaperEntity, mock_sqlite_db: SQLiteManager) -> PaperEntity:
    """Create and save a paper to the database."""
    paper_repo = PaperRepository(mock_sqlite_db)
    paper_id = paper_repo.create(mock_paper)
    mock_paper.paper_id = paper_id
    return mock_paper


@pytest.mark.asyncio
async def test_summarize_paper_success(
    saved_paper: PaperEntity,
    mock_sqlite_db: SQLiteManager,
    mock_llm_sqlite_db: LLMSQLiteManager,
    mock_summary_client: SummaryClient,
) -> None:
    """Test successful paper summarization."""
    service = PaperSummarizationService()
    await service.summarize_paper(
        saved_paper,
        mock_sqlite_db,
        mock_llm_sqlite_db,
        mock_summary_client,
    )
    summary = service.get_paper_summary(saved_paper, mock_sqlite_db)
    assert summary is not None


@pytest.mark.asyncio
async def test_summarize_paper_existing_summary(
    saved_paper: PaperEntity,
    mock_sqlite_db: SQLiteManager,
    mock_llm_sqlite_db: LLMSQLiteManager,
    mock_summary_client: SummaryClient,
) -> None:
    """Test summarization when summary already exists."""
    service = PaperSummarizationService()
    # First, create a summary
    await service.summarize_paper(
        saved_paper,
        mock_sqlite_db,
        mock_llm_sqlite_db,
        mock_summary_client,
    )

    # Then try to summarize again - should not create a new summary
    await service.summarize_paper(
        saved_paper,
        mock_sqlite_db,
        mock_llm_sqlite_db,
        mock_summary_client,
    )

    # Verify only one summary exists
    summary = service.get_paper_summary(saved_paper, mock_sqlite_db)
    assert summary is not None


@pytest.mark.asyncio
async def test_summarize_paper_force_resummarize(
    saved_paper: PaperEntity,
    mock_sqlite_db: SQLiteManager,
    mock_llm_sqlite_db: LLMSQLiteManager,
    mock_summary_client: SummaryClient,
) -> None:
    """Test summarization with force_resummarize=True."""
    service = PaperSummarizationService()
    # First, create a summary
    await service.summarize_paper(
        saved_paper,
        mock_sqlite_db,
        mock_llm_sqlite_db,
        mock_summary_client,
    )

    # Get the first summary
    first_summary = service.get_paper_summary(saved_paper, mock_sqlite_db)
    assert first_summary is not None

    # Then force resummarize
    await service.summarize_paper(
        saved_paper,
        mock_sqlite_db,
        mock_llm_sqlite_db,
        mock_summary_client,
        force_resummarize=True,
    )

    # Get the updated summary
    updated_summary = service.get_paper_summary(saved_paper, mock_sqlite_db)
    assert updated_summary is not None
    # The summary should be updated (same summary_id since we're overwriting)
    assert updated_summary.summary_id == first_summary.summary_id


@pytest.mark.asyncio
async def test_get_paper_summary_success(
    saved_paper: PaperEntity,
    mock_sqlite_db: SQLiteManager,
    mock_llm_sqlite_db: LLMSQLiteManager,
    mock_summary_client: SummaryClient,
) -> None:
    """Test getting paper summary successfully."""
    service = PaperSummarizationService()
    # First create a summary
    await service.summarize_paper(
        saved_paper,
        mock_sqlite_db,
        mock_llm_sqlite_db,
        mock_summary_client,
    )

    # Then get the summary
    result = service.get_paper_summary(saved_paper, mock_sqlite_db)

    assert result is not None
    assert result.paper_id == saved_paper.paper_id
    assert result.language == "Korean"


@pytest.mark.asyncio
async def test_get_paper_summary_fallback_to_english(
    saved_paper: PaperEntity,
    mock_sqlite_db: SQLiteManager,
    mock_llm_sqlite_db: LLMSQLiteManager,
    mock_summary_client: SummaryClient,
) -> None:
    """Test getting paper summary with fallback to English."""
    service = PaperSummarizationService()
    # Create a summary in English
    await service.summarize_paper(
        saved_paper,
        mock_sqlite_db,
        mock_llm_sqlite_db,
        mock_summary_client,
        language="English",
    )

    # Try to get Korean summary, should fallback to English
    result = service.get_paper_summary(
        saved_paper,
        mock_sqlite_db,
        language="Korean",
    )

    assert result is not None
    assert result.language == "English"


def test_get_paper_summary_not_found(
    saved_paper: PaperEntity,
    mock_sqlite_db: SQLiteManager,
) -> None:
    """Test getting paper summary when not found."""
    service = PaperSummarizationService()
    result = service.get_paper_summary(saved_paper, mock_sqlite_db)
    assert result is None


def test_get_paper_summary_no_paper_id(
    mock_sqlite_db: SQLiteManager,
) -> None:
    """Test getting paper summary when paper has no ID."""
    service = PaperSummarizationService()
    paper_without_id = PaperEntity(
        paper_id=None,
        arxiv_id="2508.01234",
        title="Test Paper Title",
        abstract="Test paper abstract",
        primary_category="cs.AI",
        categories="cs.AI,cs.LG",
        authors="Author One;Author Two",
        url_abs="https://arxiv.org/abs/2508.01234",
        url_pdf="https://arxiv.org/pdf/2508.01234",
        published_at="2023-08-01T00:00:00Z",
        updated_at="2023-08-01T00:00:00Z",
    )
    result = service.get_paper_summary(paper_without_id, mock_sqlite_db)
    assert result is None
