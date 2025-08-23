"""Pydantic models for paper-related API requests and responses."""

from typing import TYPE_CHECKING

from pydantic import BaseModel, Field, field_validator

if TYPE_CHECKING:
    from crawler.database.models import Paper as CrawlerPaper


class PaperSummary(BaseModel):
    """Model for paper summary data."""

    overview: str | None = None
    motivation: str | None = None
    method: str | None = None
    result: str | None = None
    conclusion: str | None = None
    relevance: str | None = None
    relevance_score: int | None = None


class PaperCreate(BaseModel):
    """Request model for creating a new paper."""

    url: str = Field(..., description="arXiv paper URL")
    summarize_now: bool = Field(
        default=False, description="Whether to summarize immediately"
    )
    force_refresh_metadata: bool = Field(
        default=False, description="Force refresh paper metadata"
    )
    force_resummarize: bool = Field(default=False, description="Force re-summarization")
    summary_language: str = Field(default="Korean", description="Language for summary")

    @field_validator("summary_language")
    @classmethod
    def validate_summary_language(cls, v: str) -> str:
        """Validate summary language."""
        if v not in ["Korean", "English"]:
            raise ValueError("summary_language must be 'Korean' or 'English'")
        return v


class PaperListRequest(BaseModel):
    """Request model for paper list query."""

    limit: int = Field(
        default=20, ge=1, le=100, description="Number of papers to return"
    )
    offset: int = Field(default=0, ge=0, description="Number of papers to skip")


class PaperListResponse(BaseModel):
    """Response model for paper list."""

    papers: list["PaperResponse"] = Field(..., description="List of papers")
    total_count: int = Field(..., description="Total number of papers")
    limit: int = Field(..., description="Number of papers returned")
    offset: int = Field(..., description="Number of papers skipped")
    has_more: bool = Field(..., description="Whether there are more papers available")


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
    summary: PaperSummary | None = None

    @classmethod
    def from_crawler_paper(
        cls, paper: "CrawlerPaper", summary: PaperSummary | None = None
    ) -> "PaperResponse":
        """Create PaperResponse from crawler Paper model."""
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
        )


class PaperDeleteResponse(BaseModel):
    """Response model for paper deletion."""

    success: bool
    message: str
