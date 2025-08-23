"""Paper models for the API."""

from datetime import datetime
from typing import Any

from pydantic import BaseModel, Field

from crawler.database.models import Paper as CrawlerPaper


class PaperCreate(BaseModel):
    """Paper creation model."""

    arxiv_id: str | None = Field(None, description="arXiv ID (e.g., 2508.01234)")
    url: str | None = Field(
        None, description="arXiv URL (e.g., https://arxiv.org/abs/2508.01234)"
    )
    summarize_now: bool = Field(
        True, description="Add to background queue for immediate summarization"
    )
    force_refresh_metadata: bool = Field(
        False, description="Force refresh metadata even if same version exists"
    )
    force_resummarize: bool = Field(
        False, description="Force re-summarization even if summary exists"
    )

    def model_post_init(self, __context: Any) -> None:
        """Post-initialization validation."""
        # Validate that at least one identifier is provided
        if self.arxiv_id is None and self.url is None:
            raise ValueError("Either arxiv_id or url must be provided")

        # Validate arXiv ID format if provided
        if self.arxiv_id is not None:
            if "." not in self.arxiv_id:
                raise ValueError(
                    "Invalid arXiv ID format. Expected format: YYYY.MMDDNNNN "
                    "(e.g., 2508.01234)"
                )

        # Validate arXiv URL format if provided
        if self.url is not None:
            if not self.url.startswith("https://arxiv.org/abs/"):
                raise ValueError(
                    "Invalid arXiv URL format. Expected format: "
                    "https://arxiv.org/abs/YYYY.MMDDNNNN"
                )

        # Validate that arxiv_id and url match if both are provided
        if self.arxiv_id is not None and self.url is not None:
            # Extract arXiv ID from URL
            import re

            match = re.search(r"/abs/(\d{4}\.\d{5})$", self.url)
            if match:
                url_arxiv_id = match.group(1)
                if url_arxiv_id != self.arxiv_id:
                    raise ValueError(
                        f"arXiv ID and URL do not match. "
                        f"arXiv ID: {self.arxiv_id}, URL arXiv ID: {url_arxiv_id}"
                    )
            else:
                raise ValueError("Could not extract arXiv ID from URL for comparison")


class PaperResponse(BaseModel):
    """Paper response model."""

    id: str = Field(..., description="Paper ID")
    arxiv_id: str = Field(..., description="arXiv ID")
    title: str = Field(..., description="Paper title")
    abstract: str = Field(..., description="Paper abstract")
    authors: list[str] = Field(..., description="List of authors")
    categories: list[str] = Field(..., description="arXiv categories")
    published_date: datetime = Field(..., description="Publication date")
    pdf_url: str | None = Field(None, description="PDF URL")
    summary: str | None = Field(None, description="Generated summary")
    created_at: datetime = Field(..., description="Creation timestamp")
    updated_at: datetime = Field(..., description="Last update timestamp")

    @classmethod
    def from_crawler_paper(
        cls, paper: CrawlerPaper, summary: str | None = None
    ) -> "PaperResponse":
        """Create PaperResponse from crawler Paper model."""
        return cls(
            id=str(paper.paper_id) if paper.paper_id else "unknown",
            arxiv_id=paper.arxiv_id,
            title=paper.title,
            abstract=paper.abstract,
            authors=paper.authors.split(";") if paper.authors else [],
            categories=paper.categories.split(",") if paper.categories else [],
            published_date=datetime.fromisoformat(
                paper.published_at.replace("Z", "+00:00")
            ),
            pdf_url=paper.url_pdf,
            summary=summary,
            created_at=datetime.fromisoformat(paper.updated_at.replace("Z", "+00:00")),
            updated_at=datetime.fromisoformat(paper.updated_at.replace("Z", "+00:00")),
        )


class PaperDeleteResponse(BaseModel):
    """Paper deletion response model."""

    id: str = Field(..., description="Deleted paper ID")
    arxiv_id: str = Field(..., description="Deleted paper arXiv ID")
    message: str = Field(..., description="Deletion message")
