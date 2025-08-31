"""API response models."""

from pydantic import BaseModel, Field

from core.log import get_logger
from core.models.rows import Paper, PaperBase, Summary

logger = get_logger(__name__)


class PaperResponse(PaperBase, table=False):
    """Response model for paper details."""

    # Response-specific fields
    summary: Summary | None = None
    is_starred: bool = False
    is_read: bool = False

    @classmethod
    def from_crawler_paper(
        cls,
        paper: Paper,
        summary: Summary | None = None,
        is_starred: bool = False,
        is_read: bool = False,
    ) -> "PaperResponse":
        """Create PaperResponse from Paper (SQLModel)."""

        # Create base paper data from Paper model
        paper_data = paper.model_dump()
        return cls(
            summary=summary,
            is_starred=is_starred,
            is_read=is_read,
            **paper_data,
        )


class PaperListItemResponse(PaperBase, table=False):
    """Lightweight response model for paper list items with overview only."""

    # Lightweight fields for list view
    overview: str | None = None  # Uses existing summary.overview
    has_summary: bool = False  # Flag indicating if full summary exists
    relevance: int | None = None  # Relevance score for tags
    is_starred: bool = False
    is_read: bool = False

    @classmethod
    def from_paper_with_overview(
        cls,
        paper: Paper,
        overview: str | None = None,
        has_summary: bool = False,
        relevance: int | None = None,
        is_starred: bool = False,
        is_read: bool = False,
    ) -> "PaperListItemResponse":
        """Create PaperListItemResponse from Paper with overview."""
        paper_data = paper.model_dump()
        return cls(
            overview=overview,
            has_summary=has_summary,
            relevance=relevance,
            is_starred=is_starred,
            is_read=is_read,
            **paper_data,
        )


class SummaryDetailResponse(BaseModel):
    """Response model for full summary details."""

    summary: Summary
    is_read: bool = False


class PaperOverviewData(BaseModel):
    """Model for paper overview data returned by repository."""

    paper: Paper
    overview: str | None = None
    has_summary: bool = False
    relevance: int | None = None


class PaperListResponse(BaseModel):
    """Response model for paper list with pagination."""

    papers: list[PaperResponse] = Field(..., description="List of papers")
    total_count: int = Field(..., description="Total number of papers")
    limit: int = Field(..., description="Number of papers per page")
    offset: int = Field(..., description="Number of papers skipped")
    has_more: bool = Field(..., description="Whether there are more papers")


class PaperListLightweightResponse(BaseModel):
    """Lightweight response model for paper list with overview only."""

    papers: list[PaperListItemResponse] = Field(
        ..., description="List of papers with overview"
    )
    total_count: int = Field(..., description="Total number of papers")
    limit: int = Field(..., description="Number of papers per page")
    offset: int = Field(..., description="Number of papers skipped")
    has_more: bool = Field(..., description="Whether there are more papers")


class PaperDeleteResponse(BaseModel):
    """Response model for paper deletion."""

    success: bool
    message: str


class CategoriesResponse(BaseModel):
    """Response model for preset categories."""

    categories: list[str]
    count: int


class SummaryReadResponse(BaseModel):
    """Response model for marking summary as read."""

    success: bool
    message: str
    is_read: bool = True


class StarResponse(BaseModel):
    """Response model for star operations."""

    success: bool
    message: str
    is_starred: bool
    paper_id: int | None = None
    note: str | None = None

    @classmethod
    def success_response(cls, is_starred: bool, message: str) -> "StarResponse":
        """Create a successful StarResponse."""
        return cls(success=True, is_starred=is_starred, message=message)

    @classmethod
    def failure_response(cls, message: str) -> "StarResponse":
        """Create a failed StarResponse."""
        logger.error(f"Star operation failed: {message}")
        return cls(success=False, is_starred=False, message=message)


class StarredPapersResponse(BaseModel):
    """Response model for starred papers list with pagination."""

    papers: list[PaperResponse] = Field(..., description="List of starred papers")
    total_count: int = Field(..., description="Total number of starred papers")
    limit: int = Field(..., description="Number of papers per page")
    offset: int = Field(..., description="Number of papers skipped")
    has_more: bool = Field(..., description="Whether there are more papers")


class AuthError(BaseModel):
    """Model for authentication error."""

    detail: str = Field(..., description="Error detail")
    error: str = Field(..., description="Error type")
    environment: str = Field(..., description="Environment")
