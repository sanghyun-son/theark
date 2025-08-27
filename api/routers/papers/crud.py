"""Paper CRUD operations router."""

from fastapi import APIRouter, Query

from api.dependencies import (
    CurrentUser,
    DBManager,
    SummaryClientDep,
)
from api.utils.error_handler import handle_async_api_operation
from core.models import PaperCreateRequest as PaperCreate
from core.models import (
    PaperDeleteResponse,
    PaperListResponse,
    PaperResponse,
)
from core.services.paper_service import PaperService

router = APIRouter()


@router.get("/", response_model=PaperListResponse)
async def get_papers(
    db_manager: DBManager,
    current_user: CurrentUser,
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
        current_user: Current user information

    Returns:
        List of papers with pagination metadata

    Raises:
        HTTPException: If retrieval fails
    """

    async def get_papers_operation() -> PaperListResponse:
        paper_service = PaperService()
        return await paper_service.get_papers(
            db_manager,
            current_user,
            limit=limit,
            offset=offset,
            language=language,
        )

    return await handle_async_api_operation(
        get_papers_operation, error_message="Failed to get papers"
    )


@router.post("/", response_model=PaperResponse, status_code=201)
async def create_paper(
    paper_data: PaperCreate,
    db_manager: DBManager,
    summary_client: SummaryClientDep,
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
        paper_service = PaperService()
        return await paper_service.create_paper(paper_data, db_manager, summary_client)

    return await handle_async_api_operation(
        create_paper_operation, error_message="Failed to create paper"
    )


@router.delete(
    "/{paper_identifier}",
    response_model=PaperDeleteResponse,
    operation_id="delete_paper_by_identifier",
)
async def delete_paper(
    paper_identifier: str, db_manager: DBManager
) -> PaperDeleteResponse:
    """Delete a paper by ID or arXiv ID.

    Args:
        paper_identifier: Paper ID or arXiv ID

    Returns:
        Success status and deletion information

    Raises:
        HTTPException: If paper not found
    """

    async def delete_paper_operation() -> PaperDeleteResponse:
        paper_service = PaperService()
        return await paper_service.delete_paper(paper_identifier, db_manager)

    return await handle_async_api_operation(
        delete_paper_operation,
        error_message="Failed to delete paper",
        not_found_message="Paper not found",
    )


@router.get("/{paper_identifier}", response_model=PaperResponse)
async def get_paper(
    paper_identifier: str,
    db_manager: DBManager,
) -> PaperResponse:
    """Get a paper by ID or arXiv ID.

    Args:
        paper_identifier: Paper ID or arXiv ID

    Returns:
        Paper information with summary

    Raises:
        HTTPException: If paper not found
    """

    async def get_paper_operation() -> PaperResponse:
        paper_service = PaperService()
        return await paper_service.get_paper(paper_identifier, db_manager)

    return await handle_async_api_operation(
        get_paper_operation,
        error_message="Failed to get paper",
        not_found_message="Paper not found",
    )
