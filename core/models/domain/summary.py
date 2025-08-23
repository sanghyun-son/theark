"""Summary domain models."""

from pydantic import BaseModel, Field


class SummaryContent(BaseModel):
    """Core summary content fields shared across all summary contexts."""

    overview: str | None = None
    motivation: str | None = None
    method: str | None = None
    result: str | None = None
    conclusion: str | None = None
    relevance: str | None = None
    relevance_score: int | None = Field(None, ge=0, le=10)


class Summary(BaseModel):
    """Complete summary model with metadata."""

    content: SummaryContent
    language: str = Field(..., description="Summary language (Korean or English)")
    interests: str = Field(
        ..., description="Comma-separated interests used for relevance scoring"
    )
    model: str | None = Field(None, description="LLM model used for generation")
    created_at: str | None = Field(None, description="ISO timestamp of creation")

    @classmethod
    def from_analysis_data(
        cls,
        analysis_data: dict[str, str],
        language: str,
        interests: str,
        model: str | None = None,
    ) -> "Summary":
        """Create Summary from OpenAI analysis data."""
        content = SummaryContent(
            overview=analysis_data.get("tldr"),
            motivation=analysis_data.get("motivation"),
            method=analysis_data.get("method"),
            result=analysis_data.get("result"),
            conclusion=analysis_data.get("conclusion"),
            relevance=analysis_data.get("relevance"),
            relevance_score=None,
        )
        return cls(
            content=content,
            language=language,
            interests=interests,
            model=model,
            created_at=None,
        )
