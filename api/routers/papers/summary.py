"""Paper summary operations router."""

from collections.abc import AsyncGenerator
from typing import Any

from fastapi import APIRouter, Depends
from fastapi.responses import StreamingResponse
from sqlalchemy.engine import Engine
from sqlmodel import Session

from api.dependencies import (
    get_current_user,
    get_db,
    get_engine,
    get_settings,
    get_summary_generator,
)
from api.routers.common_queries import get_summary_language_param
from api.utils.error_handler import handle_async_api_operation
from core.config import Settings
from core.database.repository.summary import SummaryRepository
from core.database.repository.summary_read import SummaryReadRepository
from core.llm.openai_client import UnifiedOpenAIClient
from core.models import PaperCreateRequest
from core.models.api.responses import SummaryDetailResponse, SummaryReadResponse
from core.models.rows import User
from core.services.paper_service import PaperService
from core.services.stream_service import StreamService

router = APIRouter()


@router.post("/stream-summary")
async def stream_paper_summary(
    paper_data: PaperCreateRequest,
    db_engine: Engine = Depends(get_engine),
    summary_client: UnifiedOpenAIClient = Depends(get_summary_generator),
    settings: Settings = Depends(get_settings),
) -> StreamingResponse:
    """Stream paper creation and summarization process.

    Args:
        paper_data: Paper data to create and summarize

    Returns:
        Server-Sent Events stream with progress updates

    Raises:
        HTTPException: If streaming fails
    """

    async def generate_stream() -> AsyncGenerator[str, None]:
        stream_service = StreamService(
            default_interests=settings.default_interests_list
        )

        with Session(db_engine) as session:
            async for event in stream_service.stream_paper_summarization(
                paper_data, session, summary_client
            ):
                yield event

    return StreamingResponse(
        generate_stream(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
        },
    )


@router.get("/{paper_id}/summary/{summary_id}")
async def get_summary(
    paper_id: int,
    summary_id: int,
    db_session: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
    settings: Settings = Depends(get_settings),
) -> dict[str, Any]:
    """Get a specific summary for a paper."""

    async def get_summary_operation() -> dict[str, Any]:
        summary_repo = SummaryRepository(db_session)
        summary = summary_repo.get_by_id(summary_id)

        if not summary:
            raise ValueError("Summary not found")

        # Early exit: Check if the summary belongs to the specified paper
        if summary.paper_id != paper_id:
            raise ValueError("Summary does not belong to the specified paper")

        return {
            "summary_id": summary.summary_id,
            "paper_id": summary.paper_id,
            "overview": summary.overview,
            "motivation": summary.motivation,
            "method": summary.method,
            "result": summary.result,
            "conclusion": summary.conclusion,
            "language": summary.language,
            "relevance": summary.relevance,
        }

    return await handle_async_api_operation(
        get_summary_operation,
        error_message="Failed to get summary",
        not_found_message="Summary not found",
    )


@router.post(
    "/{paper_id}/summary/{summary_id}/read", response_model=SummaryReadResponse
)
async def mark_summary_as_read(
    paper_id: int,
    summary_id: int,
    db_session: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> SummaryReadResponse:
    """Mark a summary as read for the current user."""

    async def mark_read_operation() -> SummaryReadResponse:
        # Get the summary directly by ID
        summary_repo = SummaryRepository(db_session)
        summary = summary_repo.get_by_id(summary_id)
        if not summary:
            raise ValueError("Summary not found")

        # Check if the summary belongs to the specified paper
        if summary.paper_id != paper_id:
            raise ValueError("Summary does not belong to the specified paper")

        # Mark the specific summary as read
        summary_read_repo = SummaryReadRepository(db_session)
        if summary.summary_id is None:
            raise ValueError("Summary has no ID")

        user_id = current_user.user_id
        if user_id is None:
            raise ValueError("User ID is required")
        success = summary_read_repo.mark_as_read(user_id, summary.summary_id)
        if not success:
            raise ValueError("Failed to mark summary as read")

        return SummaryReadResponse(
            success=True,
            message="Summary marked as read successfully",
            is_read=True,
        )

    return await handle_async_api_operation(
        mark_read_operation,
        error_message="Failed to mark summary as read",
        not_found_message="Summary not found",
    )


@router.get("/{paper_id}/summary", response_model=SummaryDetailResponse)
async def get_paper_summary(
    paper_id: int,
    language: str = Depends(get_summary_language_param),
    db_session: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> SummaryDetailResponse:
    """Get full summary for a specific paper on demand.

    This endpoint loads the full summary when user clicks on a paper,
    enabling lazy loading for better performance.

    Args:
        paper_id: Paper ID
        language: Language for summary
        current_user: Current user information

    Returns:
        Full summary details with read status

    Raises:
        HTTPException: If summary not found
    """

    async def get_paper_summary_operation() -> SummaryDetailResponse:
        paper_service = PaperService()
        user_id = current_user.user_id
        return await paper_service.get_paper_summary(
            paper_id, db_session, user_id, language
        )

    return await handle_async_api_operation(
        get_paper_summary_operation,
        error_message="Failed to get paper summary",
        not_found_message="Summary not found",
    )
