"""API request models."""

from pydantic import BaseModel, Field, field_validator


class PaperCreateRequest(BaseModel):
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
