"""Tests for background batch manager daily limit functionality."""

import pytest
from sqlalchemy.engine import Engine

from core.batch.background_manager import BackgroundBatchManager
from core.database.repository import LLMBatchRepository


@pytest.mark.asyncio
async def test_check_daily_limit_under_limit(
    mock_db_engine: Engine,
    mock_background_manager: BackgroundBatchManager,
    llm_batch_repo: LLMBatchRepository,
) -> None:

    for i in range(3):
        llm_batch_repo.create_batch_record(
            batch_id=f"batch_{i}",
            input_file_id=f"file_{i}",
            completion_window="24h",
            endpoint="/v1/chat/completions",
            entity_count=1,
        )

    result: bool = await mock_background_manager._check_daily_limit(mock_db_engine)
    assert result is True


@pytest.mark.asyncio
async def test_check_daily_limit_exceeded(
    mock_db_engine: Engine,
    mock_background_manager: BackgroundBatchManager,
    llm_batch_repo: LLMBatchRepository,
) -> None:

    for i in range(6):
        llm_batch_repo.create_batch_record(
            batch_id=f"batch_{i}",
            input_file_id=f"file_{i}",
            completion_window="24h",
            endpoint="/v1/chat/completions",
            entity_count=5,
        )

    result: bool = await mock_background_manager._check_daily_limit(mock_db_engine)
    assert result is False
