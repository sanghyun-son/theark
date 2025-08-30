"""API response models."""

from pydantic import BaseModel, Field

from core.log import get_logger
from core.models.rows import Paper, Summary

logger = get_logger(__name__)


class PaperResponse(BaseModel):
    """Response model for paper details."""

    paper_id: int
    arxiv_id: str
    title: str
    authors: list[str]
    abstract: str
    categories: list[str]
    pdf_url: str
    published_at: str | None = None
    updated_at: str | None = None
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

        return cls(
            paper_id=paper.paper_id or 0,
            arxiv_id=paper.arxiv_id,
            title=paper.title,
            authors=paper.authors.split(";") if paper.authors else [],
            abstract=paper.abstract,
            categories=paper.categories.split(",") if paper.categories else [],
            pdf_url=paper.url_pdf or "",
            published_at=paper.published_at,
            updated_at=paper.updated_at,
            summary=summary,
            is_starred=is_starred,
            is_read=is_read,
        )


class PaperListResponse(BaseModel):
    """Response model for paper list with pagination."""

    papers: list[PaperResponse] = Field(..., description="List of papers")
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
