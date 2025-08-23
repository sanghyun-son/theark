"""API response models."""

from typing import TYPE_CHECKING

from pydantic import BaseModel, Field

from core.models.domain.paper import Paper
from core.models.domain.summary import SummaryContent

if TYPE_CHECKING:
    from crawler.database import Paper as CrawlerPaper


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
    summary: SummaryContent | None = None

    @classmethod
    def from_domain_paper(cls, paper: Paper, paper_id: int = 0) -> "PaperResponse":
        """Create PaperResponse from domain Paper model."""
        return cls(
            paper_id=paper_id,
            arxiv_id=paper.metadata.arxiv_id,
            title=paper.metadata.title,
            authors=paper.metadata.authors,
            abstract=paper.metadata.abstract,
            categories=paper.metadata.categories,
            pdf_url=paper.metadata.pdf_url or "",
            published_date=paper.metadata.published_date,
            summary=paper.summary.content if paper.summary else None,
        )

    @classmethod
    def from_crawler_paper(
        cls, paper: "CrawlerPaper", summary: SummaryContent | None = None
    ) -> "PaperResponse":
        """Create PaperResponse from crawler Paper model (legacy compatibility)."""
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


class AuthError(BaseModel):
    """Model for authentication error."""

    detail: str = Field(..., description="Error detail")
    error: str = Field(..., description="Error type")
    environment: str = Field(..., description="Environment")
