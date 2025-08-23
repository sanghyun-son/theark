"""Paper domain models."""

from pydantic import BaseModel, Field, field_validator

from core.models.domain.summary import Summary


class PaperMetadata(BaseModel):
    """Core paper metadata shared across all paper contexts."""

    arxiv_id: str = Field(..., description="arXiv ID (e.g., 2101.00001)")
    title: str = Field(..., min_length=1)
    abstract: str = Field(..., min_length=1)
    authors: list[str] = Field(..., description="List of author names")
    categories: list[str] = Field(..., description="List of categories")
    published_date: str | None = Field(None, description="ISO8601 datetime")
    pdf_url: str | None = Field(None, description="PDF download URL")

    @field_validator("arxiv_id")
    @classmethod
    def validate_arxiv_id(cls, v: str) -> str:
        """Validate arXiv ID format."""
        if not v or "." not in v:
            raise ValueError("Invalid arXiv ID format")
        return v


class Paper(BaseModel):
    """Complete paper model combining metadata and summary."""

    metadata: PaperMetadata
    summary: Summary | None = None

    @classmethod
    def from_crawler_data(
        cls,
        arxiv_id: str,
        title: str,
        abstract: str,
        authors: str,
        categories: str,
        published_date: str | None = None,
        pdf_url: str | None = None,
        summary: Summary | None = None,
    ) -> "Paper":
        """Create Paper from crawler database format."""
        metadata = PaperMetadata(
            arxiv_id=arxiv_id,
            title=title,
            abstract=abstract,
            authors=authors.split(";") if authors else [],
            categories=categories.split(",") if categories else [],
            published_date=published_date,
            pdf_url=pdf_url,
        )
        return cls(metadata=metadata, summary=summary)
