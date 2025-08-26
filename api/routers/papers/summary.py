"""Paper summary operations router."""

from typing import AsyncGenerator

from fastapi import APIRouter, Request
from fastapi.responses import StreamingResponse

from api.dependencies import (
    ArxivClientDep,
    DBManager,
    PaperServiceDep,
    SummaryClientDep,
)
from api.utils.error_handler import handle_async_api_operation
from core.models import PaperCreateRequest as PaperCreate
from core.models import SummaryEntity, SummaryReadResponse

router = APIRouter()


@router.post("/stream-summary")
async def stream_paper_summary(
    request: Request,
    paper_service: PaperServiceDep,
    paper_data: PaperCreate,
    db_manager: DBManager,
    arxiv_client: ArxivClientDep,
    summary_client: SummaryClientDep,
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
        try:
            async for event in paper_service.create_paper_streaming(
                paper_data,
                db_manager,
                arxiv_client,
                summary_client,
            ):
                yield f"{event}\n\n"
        except Exception as e:
            error_event = {
                "type": "error",
                "message": str(e),
            }
            yield f"data: {error_event}\n\n"

    return StreamingResponse(
        generate_stream(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
        },
    )


@router.get("/{paper_id}/summary/{summary_id}", response_model=SummaryEntity)
async def get_summary(
    paper_service: PaperServiceDep,
    paper_id: int,
    summary_id: int,
    db_manager: DBManager,
) -> SummaryEntity:
    """Get a specific summary by ID.

    Args:
        paper_id: Paper ID
        summary_id: Summary ID

    Returns:
        Summary information

    Raises:
        HTTPException: If summary not found
    """

    async def get_summary_operation() -> SummaryEntity:
        return await paper_service.get_summary(paper_id, summary_id, db_manager)

    return await handle_async_api_operation(
        get_summary_operation,
        error_message="Failed to get summary",
        not_found_message="Summary not found",
    )


@router.post(
    "/{paper_id}/summary/{summary_id}/read", response_model=SummaryReadResponse
)
async def mark_summary_as_read(
    paper_service: PaperServiceDep,
    paper_id: int,
    summary_id: int,
    db_manager: DBManager,
) -> SummaryReadResponse:
    """Mark a summary as read.

    Args:
        paper_id: Paper ID
        summary_id: Summary ID

    Returns:
        Success status and updated read status

    Raises:
        HTTPException: If summary not found
    """

    async def mark_read_operation() -> SummaryReadResponse:
        return await paper_service.mark_summary_as_read(
            paper_id, summary_id, db_manager
        )

    return await handle_async_api_operation(
        mark_read_operation,
        error_message="Failed to mark summary as read",
        not_found_message="Summary not found",
    )
