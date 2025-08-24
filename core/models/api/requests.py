"""API request models."""

from pydantic import BaseModel, Field


class PaperCreateRequest(BaseModel):
    """Request model for creating a paper."""

    url: str = Field(..., description="arXiv URL of the paper")
    skip_auto_summarization: bool = Field(
        default=False, description="Skip automatic summarization"
    )
    summary_language: str = Field(
        default="Korean", description="Language for summary generation"
    )


class StarRequest(BaseModel):
    """Request model for star operations."""

    note: str | None = Field(
        default=None, description="Optional note for the starred paper", max_length=500
    )


class PaperListRequest(BaseModel):
    """Request model for paper list query."""

    limit: int = Field(
        default=20, ge=1, le=100, description="Number of papers to return"
    )
    offset: int = Field(default=0, ge=0, description="Number of papers to skip")
