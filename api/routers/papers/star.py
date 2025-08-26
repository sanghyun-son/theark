"""Paper star operations router."""

from fastapi import APIRouter, Query

from api.dependencies import CurrentUser, DBManager
from api.services.paper_service import PaperService
from api.utils.error_handler import handle_async_api_operation
from core.models.api.requests import StarRequest
from core.models.api.responses import StarredPapersResponse, StarResponse

router = APIRouter()


@router.post("/{paper_id}/star", response_model=StarResponse)
async def add_star(
    paper_id: int,
    star_data: StarRequest,
    db_manager: DBManager,
    current_user: CurrentUser,
) -> StarResponse:
    """Add a star to a paper.

    Args:
        paper_id: Paper ID
        star_data: Star request data
        current_user: Current user information

    Returns:
        Success status and star information

    Raises:
        HTTPException: If paper not found
    """

    async def add_star_operation() -> StarResponse:
        paper_service = PaperService()
        return await paper_service.add_star(
            paper_id, db_manager, current_user, star_data.note
        )

    return await handle_async_api_operation(
        add_star_operation,
        error_message="Failed to add star",
        not_found_message="Paper not found",
    )


@router.get("/starred/", response_model=StarredPapersResponse)
async def get_starred_papers(
    db_manager: DBManager,
    current_user: CurrentUser,
    limit: int = Query(
        default=20, ge=1, le=100, description="Number of papers to return"
    ),
    offset: int = Query(default=0, ge=0, description="Number of papers to skip"),
) -> StarredPapersResponse:
    """Get all starred papers for the current user.

    Args:
        limit: Number of papers to return (1-100)
        offset: Number of papers to skip
        current_user: Current user information

    Returns:
        List of starred papers with pagination metadata

    Raises:
        HTTPException: If retrieval fails
    """

    async def get_starred_papers_operation() -> StarredPapersResponse:
        paper_service = PaperService()
        return await paper_service.get_starred_papers(
            db_manager, current_user, limit=limit, offset=offset
        )

    return await handle_async_api_operation(
        get_starred_papers_operation, error_message="Failed to get starred papers"
    )


@router.delete("/{paper_id}/star", response_model=StarResponse)
async def remove_star(
    paper_id: int,
    db_manager: DBManager,
    current_user: CurrentUser,
) -> StarResponse:
    """Remove a star from a paper.

    Args:
        paper_id: Paper ID
        current_user: Current user information

    Returns:
        Success status

    Raises:
        HTTPException: If paper not found
    """

    async def remove_star_operation() -> StarResponse:
        paper_service = PaperService()
        return await paper_service.remove_star(paper_id, db_manager, current_user)

    return await handle_async_api_operation(
        remove_star_operation,
        error_message="Failed to remove star",
        not_found_message="Paper not found",
    )


@router.get("/{paper_id}/star", response_model=StarResponse)
async def get_star_status(
    paper_id: int,
    db_manager: DBManager,
    current_user: CurrentUser,
) -> StarResponse:
    """Check if a paper is starred by the current user.

    Args:
        paper_id: Paper ID
        current_user: Current user information

    Returns:
        Star status information

    Raises:
        HTTPException: If paper not found
    """

    async def get_star_status_operation() -> StarResponse:
        paper_service = PaperService()
        return await paper_service.is_paper_starred(paper_id, db_manager, current_user)

    return await handle_async_api_operation(
        get_star_status_operation,
        error_message="Failed to get star status",
        not_found_message="Paper not found",
    )
