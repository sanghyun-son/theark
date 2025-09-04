"""Tests for LLMRequestTracker and related functionality."""

from unittest.mock import AsyncMock

import pytest
from sqlmodel import Session

from core.database.repository import LLMRequestRepository
from core.llm.openai_client import UnifiedOpenAIClient
from core.models.external.openai import OpenAIMessage


@pytest.mark.asyncio
async def test_llm_request_tracker_success(
    mock_db_session: Session,
    mock_openai_client: UnifiedOpenAIClient,
) -> None:

    fake_model = "fake-model"
    await mock_openai_client.create_chat_completion(
        messages=[OpenAIMessage(role="user", content="Hello, world!")],
        model=fake_model,
        db_session=mock_db_session,
    )
    repo = LLMRequestRepository(mock_db_session)
    requests = repo.get_requests_by_status("success")
    assert len(requests) == 1


@pytest.mark.asyncio
async def test_llm_request_tracker_error(
    mock_db_session: Session,
    mock_openai_client: UnifiedOpenAIClient,
) -> None:

    fake_model = "fake-model"
    mock_create = AsyncMock(side_effect=RuntimeError("Test error"))
    mock_openai_client._client.chat.completions.create = mock_create
    with pytest.raises(RuntimeError):
        await mock_openai_client.create_chat_completion(
            messages=[OpenAIMessage(role="user", content="Hello, world!")],
            model=fake_model,
            db_session=mock_db_session,
        )

    repo = LLMRequestRepository(mock_db_session)
    requests = repo.get_requests_by_status("error")
    assert len(requests) == 1
