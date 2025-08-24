"""Paper API endpoints router."""

from typing import AsyncGenerator

from fastapi import APIRouter, Query, Request
from fastapi.responses import StreamingResponse

from api.dependencies import DBManager, LLMDBManager, PaperServiceDep
from api.utils.error_handler import handle_async_api_operation
from core.models import PaperCreateRequest as PaperCreate
from core.models import (
    PaperDeleteResponse,
    PaperListResponse,
    PaperResponse,
    SummaryEntity,
)
from core.models.api.requests import StarRequest
from core.models.api.responses import (
    StarredPapersResponse,
    StarResponse,
    SummaryReadResponse,
)

router = APIRouter(prefix="/v1/papers", tags=["papers"])


@router.get("/", response_model=PaperListResponse)
async def get_papers(
    paper_service: PaperServiceDep,
    db_manager: DBManager,
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

    async def get_papers_operation() -> PaperListResponse:
        return await paper_service.get_papers(
            db_manager, limit=limit, offset=offset, language=language
        )

    return await handle_async_api_operation(
        get_papers_operation, error_message="Failed to get papers"
    )


@router.post("/", response_model=PaperResponse, status_code=201)
async def create_paper(
    paper_service: PaperServiceDep,
    paper_data: PaperCreate,
    db_manager: DBManager,
    llm_db_manager: LLMDBManager,
) -> PaperResponse:
    """Create a new paper.

    Args:
        paper_data: Paper data to create

    Returns:
        Created paper with ID and timestamps

    Raises:
        HTTPException: If paper creation fails
    """

    async def create_paper_operation() -> PaperResponse:
        return await paper_service.create_paper(paper_data, db_manager, llm_db_manager)

    return await handle_async_api_operation(
        create_paper_operation, error_message="Failed to create paper"
    )


@router.delete(
    "/{paper_identifier}",
    response_model=PaperDeleteResponse,
    operation_id="delete_paper_by_identifier",
)
async def delete_paper(
    paper_service: PaperServiceDep, paper_identifier: str, db_manager: DBManager
) -> PaperDeleteResponse:
    """Delete a paper by ID or arXiv ID.

    Args:
        paper_identifier: Paper ID or arXiv ID

    Returns:
        Deletion result with success status and message

    Raises:
        HTTPException: If deletion fails
    """

    async def delete_paper_operation() -> PaperDeleteResponse:
        return await paper_service.delete_paper(paper_identifier, db_manager)

    return await handle_async_api_operation(
        delete_paper_operation,
        error_message="Failed to delete paper",
        not_found_message="Paper not found",
    )


@router.post("/stream-summary", status_code=200)
async def stream_paper_summary(
    paper_service: PaperServiceDep,
    paper_data: PaperCreate,
    db_manager: DBManager,
    llm_db_manager: LLMDBManager,
    request: Request,
) -> StreamingResponse:
    """Create a paper and stream the summarization progress.

    Args:
        paper_data: Paper data to create

    Returns:
        Streaming response with summarization progress and final result
    """

    async def generate_stream() -> AsyncGenerator[str, None]:
        # Try to get ArxivClient from app state (for testing)
        arxiv_client = getattr(request.app.state, "arxiv_client", None)
        async for event in paper_service.stream_paper_creation(
            paper_data, db_manager, llm_db_manager, arxiv_client
        ):
            yield event

    return StreamingResponse(
        generate_stream(),
        media_type="text/event-stream",
        headers={"Cache-Control": "no-cache", "Connection": "keep-alive"},
    )


@router.get("/{paper_identifier}", response_model=PaperResponse)
async def get_paper(
    paper_service: PaperServiceDep,
    paper_identifier: str,
    db_manager: DBManager,
    llm_db_manager: LLMDBManager,
) -> PaperResponse:
    """Get a paper by ID or arXiv ID.

    Args:
        paper_identifier: Paper ID or arXiv ID

    Returns:
        Paper with details and summary if available

    Raises:
        HTTPException: If paper not found
    """

    async def get_paper_operation() -> PaperResponse:
        return await paper_service.get_paper(
            paper_identifier, db_manager, llm_db_manager
        )

    return await handle_async_api_operation(
        get_paper_operation,
        error_message="Failed to get paper",
        not_found_message="Paper not found",
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
        Summary details

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


@router.post("/{paper_id}/star", response_model=StarResponse)
async def add_star(
    paper_service: PaperServiceDep,
    paper_id: int,
    star_data: StarRequest,
    db_manager: DBManager,
) -> StarResponse:
    """Add a star to a paper.

    Args:
        paper_id: Paper ID
        star_data: Star request data

    Returns:
        Success status and star information

    Raises:
        HTTPException: If paper not found
    """

    async def add_star_operation() -> StarResponse:
        return await paper_service.add_star(paper_id, db_manager, star_data.note)

    return await handle_async_api_operation(
        add_star_operation,
        error_message="Failed to add star",
        not_found_message="Paper not found",
    )


@router.delete("/{paper_id}/star", response_model=StarResponse)
async def remove_star(
    paper_service: PaperServiceDep, paper_id: int, db_manager: DBManager
) -> StarResponse:
    """Remove a star from a paper.

    Args:
        paper_id: Paper ID

    Returns:
        Success status

    Raises:
        HTTPException: If paper not found
    """

    async def remove_star_operation() -> StarResponse:
        return await paper_service.remove_star(paper_id, db_manager)

    return await handle_async_api_operation(
        remove_star_operation,
        error_message="Failed to remove star",
        not_found_message="Paper not found",
    )


@router.get("/starred", response_model=StarredPapersResponse)
async def get_starred_papers(
    paper_service: PaperServiceDep,
    db_manager: DBManager,
    limit: int = Query(
        default=20, ge=1, le=100, description="Number of papers to return"
    ),
    offset: int = Query(default=0, ge=0, description="Number of papers to skip"),
) -> StarredPapersResponse:
    """Get all starred papers for the current user.

    Args:
        limit: Number of papers to return (1-100)
        offset: Number of papers to skip

    Returns:
        List of starred papers with pagination metadata

    Raises:
        HTTPException: If retrieval fails
    """

    async def get_starred_papers_operation() -> StarredPapersResponse:
        return await paper_service.get_starred_papers(
            db_manager, limit=limit, offset=offset
        )

    return await handle_async_api_operation(
        get_starred_papers_operation, error_message="Failed to get starred papers"
    )


@router.get("/{paper_id}/star", response_model=StarResponse)
async def get_star_status(
    paper_service: PaperServiceDep, paper_id: int, db_manager: DBManager
) -> StarResponse:
    """Check if a paper is starred by the current user.

    Args:
        paper_id: Paper ID

    Returns:
        Star status information

    Raises:
        HTTPException: If paper not found
    """

    async def get_star_status_operation() -> StarResponse:
        return await paper_service.is_paper_starred(paper_id, db_manager)

    return await handle_async_api_operation(
        get_star_status_operation,
        error_message="Failed to get star status",
        not_found_message="Paper not found",
    )
