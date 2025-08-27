"""API response models."""

from pydantic import BaseModel, Field

from core.models.database.entities import PaperEntity, SummaryEntity


class PaperResponse(BaseModel):
    """Response model for paper details."""

    paper_id: int
    arxiv_id: str
    title: str
    authors: list[str]
    abstract: str
    categories: list[str]
    pdf_url: str
    published_date: str | None = None
    summary: SummaryEntity | None = None
    is_starred: bool = False

    @classmethod
    def from_crawler_paper(
        cls,
        paper: PaperEntity,
        summary: SummaryEntity | None = None,
        is_starred: bool = False,
    ) -> "PaperResponse":
        """Create PaperResponse from PaperEntity (legacy compatibility)."""
        return cls(
            paper_id=paper.paper_id or 0,
            arxiv_id=paper.arxiv_id,
            title=paper.title,
            authors=paper.authors.split(";") if paper.authors else [],
            abstract=paper.abstract,
            categories=paper.categories.split(",") if paper.categories else [],
            pdf_url=paper.url_pdf or "",
            published_date=paper.published_at,
            summary=summary,
            is_starred=is_starred,
        )


class PaperListResponse(BaseModel):
    """Response model for paper list."""

    papers: list[PaperResponse] = Field(..., description="List of papers")
    total_count: int = Field(..., description="Total number of papers")
    limit: int = Field(..., description="Number of papers returned")
    offset: int = Field(..., description="Number of papers skipped")
    has_more: bool = Field(..., description="Whether there are more papers available")


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
    summary_id: int
    is_read: bool


class StarResponse(BaseModel):
    """Response model for star operations."""

    success: bool
    message: str
    paper_id: int
    is_starred: bool
    note: str | None = None
    created_at: str | None = None


class StarredPapersResponse(BaseModel):
    """Response model for starred papers list."""

    papers: list[PaperResponse]
    total_count: int
    limit: int
    offset: int


class AuthError(BaseModel):
    """Model for authentication error."""

    detail: str = Field(..., description="Error detail")
    error: str = Field(..., description="Error type")
    environment: str = Field(..., description="Environment")
