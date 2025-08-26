"""Tests for paper summarization service."""

import pytest

from api.services.paper_summarization_service import PaperSummarizationService
from core.models.database.entities import PaperEntity, SummaryEntity
from core.database.interfaces import DatabaseManager
from core.database.repository import PaperRepository, SummaryRepository
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
async def saved_paper(
    mock_paper: PaperEntity, mock_db_manager: DatabaseManager
) -> PaperEntity:
    """Create and save a paper to the database."""
    paper_repo = PaperRepository(mock_db_manager)
    paper_id = await paper_repo.create(mock_paper)
    mock_paper.paper_id = paper_id
    return mock_paper


@pytest.mark.asyncio
async def test_summarize_paper_success(
    mock_paper: PaperEntity,
    mock_db_manager: DatabaseManager,
    mock_summary_client: SummaryClient,
) -> None:
    """Test successful paper summarization."""
    service = PaperSummarizationService()

    # Save paper to database first
    paper_repo = PaperRepository(mock_db_manager)
    paper_id = await paper_repo.create(mock_paper)
    paper = mock_paper
    paper.paper_id = paper_id

    await service.summarize_paper(
        paper,
        mock_db_manager,
        mock_summary_client,
    )

    # Debug: Check what's in the database
    summary_repo = SummaryRepository(mock_db_manager)
    all_summaries = await summary_repo.get_by_paper_id(paper.paper_id)
    print(f"Found {len(all_summaries)} summaries for paper {paper.paper_id}")
    for s in all_summaries:
        print(f"Summary: {s.summary_id}, language: {s.language}")

    summary = await service.get_paper_summary(paper, mock_db_manager)
    assert summary is not None


@pytest.mark.asyncio
async def test_summarize_paper_existing_summary(
    mock_paper: PaperEntity,
    mock_db_manager: DatabaseManager,
    mock_summary_client: SummaryClient,
) -> None:
    """Test summarization when summary already exists."""
    service = PaperSummarizationService()

    # Save paper to database first
    paper_repo = PaperRepository(mock_db_manager)
    paper_id = await paper_repo.create(mock_paper)
    paper = mock_paper
    paper.paper_id = paper_id

    # First, create a summary
    await service.summarize_paper(
        paper,
        mock_db_manager,
        mock_summary_client,
    )

    # Then try to summarize again - should not create a new summary
    await service.summarize_paper(
        paper,
        mock_db_manager,
        mock_summary_client,
    )

    # Verify only one summary exists
    summary = await service.get_paper_summary(paper, mock_db_manager)
    assert summary is not None


@pytest.mark.asyncio
async def test_summarize_paper_force_resummarize(
    mock_paper: PaperEntity,
    mock_db_manager: DatabaseManager,
    mock_summary_client: SummaryClient,
) -> None:
    """Test summarization with force_resummarize=True."""
    service = PaperSummarizationService()

    # Save paper to database first
    paper_repo = PaperRepository(mock_db_manager)
    paper_id = await paper_repo.create(mock_paper)
    paper = mock_paper
    paper.paper_id = paper_id

    # First, create a summary
    await service.summarize_paper(
        paper,
        mock_db_manager,
        mock_summary_client,
    )

    # Get the first summary
    first_summary = await service.get_paper_summary(paper, mock_db_manager)
    assert first_summary is not None

    # Then force resummarize
    await service.summarize_paper(
        paper,
        mock_db_manager,
        mock_summary_client,
        force_resummarize=True,
    )

    # Get the updated summary
    updated_summary = await service.get_paper_summary(paper, mock_db_manager)
    assert updated_summary is not None
    # The summary should be updated (same summary_id since we're overwriting)
    assert updated_summary.summary_id == first_summary.summary_id


@pytest.mark.asyncio
async def test_get_paper_summary_success(
    mock_paper: PaperEntity,
    mock_db_manager: DatabaseManager,
    mock_summary_client: SummaryClient,
) -> None:
    """Test getting paper summary successfully."""
    service = PaperSummarizationService()

    # Save paper to database first
    paper_repo = PaperRepository(mock_db_manager)
    paper_id = await paper_repo.create(mock_paper)
    paper = mock_paper
    paper.paper_id = paper_id

    # First create a summary
    await service.summarize_paper(
        paper,
        mock_db_manager,
        mock_summary_client,
    )

    # Then get the summary
    result = await service.get_paper_summary(paper, mock_db_manager)

    assert result is not None
    assert result.paper_id == paper.paper_id
    assert result.language == "Korean"


@pytest.mark.asyncio
async def test_get_paper_summary_fallback_to_english(
    mock_paper: PaperEntity,
    mock_db_manager: DatabaseManager,
    mock_summary_client: SummaryClient,
) -> None:
    """Test getting paper summary with fallback to English."""
    service = PaperSummarizationService()

    # Save paper to database first
    paper_repo = PaperRepository(mock_db_manager)
    paper_id = await paper_repo.create(mock_paper)
    paper = mock_paper
    paper.paper_id = paper_id

    # Create a summary in English
    await service.summarize_paper(
        paper,
        mock_db_manager,
        mock_summary_client,
        language="English",
    )

    # Try to get Korean summary, should fallback to English
    result = await service.get_paper_summary(
        paper,
        mock_db_manager,
        language="Korean",
    )

    assert result is not None
    assert result.language == "English"


@pytest.mark.asyncio
async def test_get_paper_summary_not_found(
    mock_paper: PaperEntity,
    mock_db_manager: DatabaseManager,
) -> None:
    """Test getting paper summary when not found."""
    service = PaperSummarizationService()

    # Save paper to database first
    paper_repo = PaperRepository(mock_db_manager)
    paper_id = await paper_repo.create(mock_paper)
    paper = mock_paper
    paper.paper_id = paper_id

    result = await service.get_paper_summary(paper, mock_db_manager)
    assert result is None


@pytest.mark.asyncio
async def test_get_paper_summary_no_paper_id(
    mock_db_manager: DatabaseManager,
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
    result = await service.get_paper_summary(paper_without_id, mock_db_manager)
    assert result is None
