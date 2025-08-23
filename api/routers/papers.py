"""Paper API endpoints router."""

from typing import AsyncGenerator

from fastapi import APIRouter, Query, Request
from fastapi.responses import StreamingResponse

from api.services.paper_service import PaperService
from api.services.streaming_service import StreamingService
from api.utils.error_handler import handle_async_api_operation
from core.models import PaperCreateRequest as PaperCreate
from core.models import (
    PaperDeleteResponse,
    PaperListResponse,
    PaperResponse,
    SummaryEntity,
)
from core.models.api.responses import SummaryReadResponse

router = APIRouter(prefix="/v1/papers", tags=["papers"])


@router.get("/", response_model=PaperListResponse)
async def get_papers(
    request: Request,
    limit: int = Query(
        default=20, ge=1, le=100, description="Number of papers to return"
    ),
    offset: int = Query(default=0, ge=0, description="Number of papers to skip"),
    language: str = Query(default="Korean", description="Language for summaries"),
) -> PaperListResponse:
    """Get papers with pagination.

    Args:
        limit: Number of papers to return (1-100)
        offset: Number of papers to skip

    Returns:
        List of papers with pagination metadata

    Raises:
        HTTPException: If retrieval fails
    """
    paper_service: PaperService = request.app.state.paper_service

    async def get_papers_operation() -> PaperListResponse:
        return await paper_service.get_papers(
            limit=limit, offset=offset, language=language
        )

    return await handle_async_api_operation(
        get_papers_operation, error_message="Failed to get papers"
    )


@router.post("/", response_model=PaperResponse, status_code=201)
async def create_paper(request: Request, paper_data: PaperCreate) -> PaperResponse:
    """Create a new paper.

    Args:
        paper_data: Paper data to create

    Returns:
        Created paper with ID and timestamps

    Raises:
        HTTPException: If paper creation fails
    """
    paper_service: PaperService = request.app.state.paper_service

    async def create_paper_operation() -> PaperResponse:
        return await paper_service.create_paper(paper_data)

    return await handle_async_api_operation(
        create_paper_operation, error_message="Failed to create paper"
    )


@router.delete(
    "/{paper_identifier}",
    response_model=PaperDeleteResponse,
    operation_id="delete_paper_by_identifier",
)
async def delete_paper(request: Request, paper_identifier: str) -> PaperDeleteResponse:
    """Delete a paper by ID or arXiv ID.

    Args:
        paper_identifier: Paper ID or arXiv ID

    Returns:
        Deletion result with success status and message

    Raises:
        HTTPException: If deletion fails
    """
    paper_service: PaperService = request.app.state.paper_service

    async def delete_paper_operation() -> PaperDeleteResponse:
        return await paper_service.delete_paper(paper_identifier)

    return await handle_async_api_operation(
        delete_paper_operation,
        error_message="Failed to delete paper",
        not_found_message="Paper not found",
    )


@router.post("/stream-summary", status_code=200)
async def stream_paper_summary(
    request: Request, paper_data: PaperCreate
) -> StreamingResponse:
    """Create a paper and stream the summarization progress.

    Args:
        paper_data: Paper data to create

    Returns:
        Streaming response with summarization progress and final result
    """
    paper_service: PaperService = request.app.state.paper_service
    streaming_service = StreamingService(paper_service)

    async def generate_stream() -> AsyncGenerator[str, None]:
        async for event in streaming_service.stream_paper_creation(paper_data):
            yield event

    return StreamingResponse(
        generate_stream(),
        media_type="text/plain",
        headers={"Cache-Control": "no-cache", "Connection": "keep-alive"},
    )


@router.get("/{paper_identifier}", response_model=PaperResponse)
async def get_paper(request: Request, paper_identifier: str) -> PaperResponse:
    """Get a paper by ID or arXiv ID.

    Args:
        paper_identifier: Paper ID or arXiv ID

    Returns:
        Paper with details and summary if available

    Raises:
        HTTPException: If paper not found
    """
    paper_service: PaperService = request.app.state.paper_service

    async def get_paper_operation() -> PaperResponse:
        return await paper_service.get_paper(paper_identifier)

    return await handle_async_api_operation(
        get_paper_operation,
        error_message="Failed to get paper",
        not_found_message="Paper not found",
    )


@router.get("/{paper_id}/summary/{summary_id}", response_model=SummaryEntity)
async def get_summary(
    request: Request, paper_id: int, summary_id: int
) -> SummaryEntity:
    """Get a specific summary by ID.

    Args:
        paper_id: Paper ID
        summary_id: Summary ID

    Returns:
        Summary details

    Raises:
        HTTPException: If summary not found
    """
    paper_service: PaperService = request.app.state.paper_service

    async def get_summary_operation() -> SummaryEntity:
        return await paper_service.get_summary(paper_id, summary_id)

    return await handle_async_api_operation(
        get_summary_operation,
        error_message="Failed to get summary",
        not_found_message="Summary not found",
    )


@router.post(
    "/{paper_id}/summary/{summary_id}/read", response_model=SummaryReadResponse
)
async def mark_summary_as_read(
    request: Request, paper_id: int, summary_id: int
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
    paper_service: PaperService = request.app.state.paper_service

    async def mark_read_operation() -> SummaryReadResponse:
        return await paper_service.mark_summary_as_read(paper_id, summary_id)

    return await handle_async_api_operation(
        mark_read_operation,
        error_message="Failed to mark summary as read",
        not_found_message="Summary not found",
    )
