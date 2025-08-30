"""Tests for paper summarization service."""

import pytest
from sqlmodel import Session

from core.llm.openai_client import UnifiedOpenAIClient
from core.models.rows import Paper
from core.services.paper_summarization_service import PaperSummarizationService


@pytest.mark.asyncio
async def test_summarize_paper_success(
    saved_paper: Paper,
    mock_openai_client: UnifiedOpenAIClient,
    mock_db_session: Session,
) -> None:

    service = PaperSummarizationService()
    response = await service.summarize_paper(
        saved_paper,
        mock_db_session,
        mock_openai_client,
    )
    assert response is not None
    assert response.overview is not None


@pytest.mark.asyncio
async def test_summarize_paper_existing_summary(
    saved_paper: Paper,
    mock_db_session: Session,
    mock_openai_client: UnifiedOpenAIClient,
) -> None:

    service = PaperSummarizationService()
    await service.summarize_paper(
        saved_paper,
        mock_db_session,
        mock_openai_client,
    )
    await service.summarize_paper(
        saved_paper,
        mock_db_session,
        mock_openai_client,
    )
    summary = await service.get_summary(saved_paper.paper_id, mock_db_session)
    assert summary is not None


@pytest.mark.asyncio
async def test_summarize_paper_force_resummarize(
    saved_paper: Paper,
    mock_db_session: Session,
    mock_openai_client: UnifiedOpenAIClient,
) -> None:

    service = PaperSummarizationService()
    await service.summarize_paper(
        saved_paper,
        mock_db_session,
        mock_openai_client,
    )

    first_summary = await service.get_summary(saved_paper.paper_id, mock_db_session)
    assert first_summary is not None

    await service.summarize_paper(
        saved_paper,
        mock_db_session,
        mock_openai_client,
        force_resummarize=True,
    )

    updated_summary = await service.get_summary(saved_paper.paper_id, mock_db_session)
    assert updated_summary is not None
    assert updated_summary.summary_id == first_summary.summary_id


@pytest.mark.asyncio
async def test_get_paper_summary_success(
    saved_paper: Paper,
    mock_db_session: Session,
    mock_openai_client: UnifiedOpenAIClient,
) -> None:

    service = PaperSummarizationService()
    await service.summarize_paper(
        saved_paper,
        mock_db_session,
        mock_openai_client,
    )

    result = await service.get_summary(saved_paper.paper_id, mock_db_session)

    assert result is not None
    assert result.paper_id == saved_paper.paper_id
    assert result.language == "Korean"


@pytest.mark.asyncio
async def test_get_paper_summary_fallback_to_english(
    saved_paper: Paper,
    mock_db_session: Session,
    mock_openai_client: UnifiedOpenAIClient,
) -> None:

    service = PaperSummarizationService()
    await service.summarize_paper(
        saved_paper,
        mock_db_session,
        mock_openai_client,
        language="English",
    )

    result = await service.get_summary(
        saved_paper.paper_id,
        mock_db_session,
        language="Korean",
    )

    assert result is not None
    assert result.language == "English"


@pytest.mark.asyncio
async def test_get_paper_summary_not_found(
    saved_paper: Paper,
    mock_db_session: Session,
) -> None:

    service = PaperSummarizationService()
    result = await service.get_summary(saved_paper.paper_id, mock_db_session)
    assert result is None


@pytest.mark.asyncio
async def test_get_paper_summary_no_paper_id(
    mock_db_session: Session,
) -> None:

    service = PaperSummarizationService()
    result = await service.get_summary(None, mock_db_session)
    assert result is None
