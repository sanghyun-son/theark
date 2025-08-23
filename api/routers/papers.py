"""Paper API endpoints router."""

from fastapi import APIRouter, HTTPException, Request, status

from api.models.paper import PaperCreate, PaperDeleteResponse, PaperResponse
from api.services.paper_service import PaperService

router = APIRouter(prefix="/v1/papers", tags=["papers"])


# Database initialization will be handled in the main app startup


@router.post("/", response_model=PaperResponse, status_code=status.HTTP_201_CREATED)
async def create_paper(request: Request, paper_data: PaperCreate) -> PaperResponse:
    """Create a new paper.

    Args:
        paper_data: Paper data to create

    Returns:
        Created paper with ID and timestamps

    Raises:
        HTTPException: If paper creation fails
    """
    try:
        # TODO: Add validation logic here
        # 1. Validate arXiv ID/URL format (handled by Pydantic model)
        # 2. Check if paper already exists
        # 3. Handle summarization queue logic

        # Get paper service from app state
        paper_service: PaperService = request.app.state.paper_service

        # Create paper using service
        paper = await paper_service.create_paper(paper_data)
        return paper

    except ValueError as e:
        # Handle validation errors
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))
    except Exception:
        # Handle unexpected errors
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to create paper",
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
    try:
        # Get paper service from app state
        paper_service: PaperService = request.app.state.paper_service

        # Get paper using service
        paper = await paper_service.get_paper(paper_identifier)
        return paper

    except ValueError as e:
        # Handle not found errors
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))
    except Exception:
        # Handle unexpected errors
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to get paper",
        )


@router.delete("/{paper_identifier}", response_model=PaperDeleteResponse)
async def delete_paper(request: Request, paper_identifier: str) -> PaperDeleteResponse:
    """Delete a paper by ID or arXiv ID.

    Args:
        paper_identifier: Paper ID or arXiv ID

    Returns:
        Deletion response with paper details

    Raises:
        HTTPException: If paper not found or deletion fails
    """
    try:
        # TODO: Add validation logic here
        # 1. Validate identifier format
        # 2. Check if paper exists

        # Get paper service from app state
        paper_service: PaperService = request.app.state.paper_service

        # Delete paper using service
        result = await paper_service.delete_paper(paper_identifier)
        return result

    except ValueError as e:
        # Handle not found errors
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))
    except Exception:
        # Handle unexpected errors
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to delete paper",
        )
