"""Paper CRUD operations router."""

from fastapi import APIRouter, Depends, Query
from sqlmodel import Session

from api.dependencies import (
    get_current_user,
    get_db,
    get_summary_generator,
)
from api.utils.error_handler import handle_async_api_operation
from core.database.repository.paper import PaperRepository
from core.llm.openai_client import UnifiedOpenAIClient
from core.models import (
    PaperCreateRequest,
    PaperDeleteResponse,
    PaperListLightweightResponse,
    PaperListResponse,
    PaperResponse,
)
from core.models.rows import User
from core.services.paper_service import PaperService

router = APIRouter()


@router.get("/", response_model=PaperListResponse)
async def get_papers(
    db_session: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
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
        user_id = current_user.user_id
        return await paper_service.get_papers(
            db_session,
            user_id,
            skip=offset,  # Convert offset to skip
            limit=limit,
            language=language,
        )

    return await handle_async_api_operation(
        get_papers_operation, error_message="Failed to get papers"
    )


@router.get("/lightweight", response_model=PaperListLightweightResponse)
async def get_papers_lightweight(
    db_session: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
    limit: int = Query(
        default=20, ge=1, le=100, description="Number of papers to return"
    ),
    offset: int = Query(default=0, ge=0, description="Number of papers to skip"),
    language: str = Query(default="Korean", description="Language for summaries"),
) -> PaperListLightweightResponse:
    """Get papers with overview only for better performance.

    This endpoint returns papers with only overview (not full summaries)
    for improved frontend performance. Full summaries are loaded on demand.

    Args:
        limit: Number of papers to return (1-100)
        offset: Number of papers to skip
        language: Language for summaries
        current_user: Current user information

    Returns:
        Lightweight list of papers with overview only

    Raises:
        HTTPException: If retrieval fails
    """

    async def get_papers_lightweight_operation() -> PaperListLightweightResponse:
        paper_service = PaperService()
        user_id = current_user.user_id
        return await paper_service.get_papers_lightweight(
            db_session,
            user_id,
            skip=offset,  # Convert offset to skip
            limit=limit,
            language=language,
        )

    return await handle_async_api_operation(
        get_papers_lightweight_operation, error_message="Failed to get papers"
    )


@router.post("/", response_model=PaperResponse, status_code=201)
async def create_paper(
    paper_data: PaperCreateRequest,
    db_session: Session = Depends(get_db),
    summary_client: UnifiedOpenAIClient = Depends(get_summary_generator),
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
        paper_repo = PaperRepository(db_session)
        paper_service = PaperService()
        return await paper_service.create_paper(paper_data, paper_repo, summary_client)

    return await handle_async_api_operation(
        create_paper_operation, error_message="Failed to create paper"
    )


@router.delete(
    "/{paper_identifier}",
    response_model=PaperDeleteResponse,
    operation_id="delete_paper_by_identifier",
)
async def delete_paper(
    paper_identifier: str,
    db_session: Session = Depends(get_db),
) -> PaperDeleteResponse:
    """Delete a paper by ID or arXiv ID.

    Args:
        paper_identifier: Paper ID or arXiv ID

    Returns:
        Deletion confirmation

    Raises:
        HTTPException: If paper deletion fails
    """

    async def delete_paper_operation() -> PaperDeleteResponse:
        paper_service = PaperService()
        return paper_service.delete_paper(paper_identifier, db_session)

    return await handle_async_api_operation(
        delete_paper_operation,
        error_message="Failed to delete paper",
        not_found_message="Paper not found",
    )


@router.get("/{paper_identifier}", response_model=PaperResponse)
async def get_paper(
    paper_identifier: str,
    db_session: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
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
        user_id = current_user.user_id
        return await paper_service.get_paper(paper_identifier, db_session, user_id)

    return await handle_async_api_operation(
        get_paper_operation,
        error_message="Failed to get paper",
        not_found_message="Paper not found",
    )
