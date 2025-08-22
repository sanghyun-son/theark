"""Pydantic models for database entities."""

from datetime import datetime

from pydantic import BaseModel, Field, field_validator


class Paper(BaseModel):
    """Paper entity model."""

    paper_id: int | None = None
    arxiv_id: str = Field(..., description="arXiv ID (e.g., 2101.00001)")
    latest_version: int = Field(default=1, ge=1)
    title: str = Field(..., min_length=1)
    abstract: str = Field(..., min_length=1)
    primary_category: str = Field(..., description="Primary category (e.g., cs.CL)")
    categories: str = Field(..., description="Comma-separated categories")
    authors: str = Field(..., description="Semicolon-separated authors")
    url_abs: str = Field(..., description="Abstract URL")
    url_pdf: str | None = None
    published_at: str = Field(..., description="ISO8601 datetime")
    updated_at: str = Field(..., description="ISO8601 datetime")

    @field_validator("arxiv_id")
    @classmethod
    def validate_arxiv_id(cls, v: str) -> str:
        """Validate arXiv ID format."""
        if not v or "." not in v:
            raise ValueError("Invalid arXiv ID format")
        return v

    @field_validator("primary_category")
    @classmethod
    def validate_primary_category(cls, v: str) -> str:
        """Validate primary category format."""
        if not v or "." not in v:
            raise ValueError("Invalid category format (e.g., cs.CL)")
        return v

    @field_validator("published_at", "updated_at")
    @classmethod
    def validate_datetime(cls, v: str) -> str:
        """Validate ISO8601 datetime format."""
        try:
            datetime.fromisoformat(v.replace("Z", "+00:00"))
            return v
        except ValueError:
            raise ValueError("Invalid ISO8601 datetime format")


class Summary(BaseModel):
    """Summary entity model."""

    summary_id: int | None = None
    paper_id: int = Field(..., gt=0)
    version: int = Field(..., ge=1)
    overview: str = Field(..., min_length=1, description="Paper overview")
    motivation: str = Field(..., min_length=1, description="Research motivation")
    method: str = Field(..., min_length=1, description="Methodology")
    result: str = Field(..., min_length=1, description="Results")
    conclusion: str = Field(..., min_length=1, description="Conclusion")
    language: str = Field(..., description="Summary language (Korean or English)")
    interests: str = Field(..., description="Comma-separated interests")
    relevance: int = Field(..., ge=0, le=10, description="Relevance score (0-10)")
    model: str | None = None
    created_at: str | None = None

    @field_validator("language")
    @classmethod
    def validate_language(cls, v: str) -> str:
        """Validate summary language."""
        valid_languages = {"Korean", "English"}
        if v not in valid_languages:
            raise ValueError(f"Invalid language. Must be one of: {valid_languages}")
        return v


class AppUser(BaseModel):
    """Application user model."""

    user_id: int | None = None
    email: str = Field(..., description="User email address")
    display_name: str | None = None

    @field_validator("email")
    @classmethod
    def validate_email(cls, v: str) -> str:
        """Validate email format."""
        if "@" not in v or "." not in v:
            raise ValueError("Invalid email format")
        return v.lower()


class UserInterest(BaseModel):
    """User interest model."""

    user_id: int = Field(..., gt=0)
    kind: str = Field(..., description="Interest kind (category, keyword, author)")
    value: str = Field(..., min_length=1)
    weight: float = Field(default=1.0, ge=0.0, le=10.0)

    @field_validator("kind")
    @classmethod
    def validate_kind(cls, v: str) -> str:
        """Validate interest kind."""
        valid_kinds = {"category", "keyword", "author"}
        if v not in valid_kinds:
            raise ValueError(f"Invalid kind. Must be one of: {valid_kinds}")
        return v


class UserStar(BaseModel):
    """User star/bookmark model."""

    user_id: int = Field(..., gt=0)
    paper_id: int = Field(..., gt=0)
    note: str | None = None
    created_at: str | None = None


class FeedItem(BaseModel):
    """Feed item model."""

    feed_item_id: int | None = None
    user_id: int = Field(..., gt=0)
    paper_id: int = Field(..., gt=0)
    score: float = Field(..., ge=0.0)
    feed_date: str = Field(..., description="YYYY-MM-DD format")
    created_at: str | None = None

    @field_validator("feed_date")
    @classmethod
    def validate_feed_date(cls, v: str) -> str:
        """Validate feed date format."""
        try:
            datetime.strptime(v, "%Y-%m-%d")
            return v
        except ValueError:
            raise ValueError("Invalid date format. Use YYYY-MM-DD")


class CrawlEvent(BaseModel):
    """Crawl event model."""

    event_id: int | None = None
    arxiv_id: str | None = None
    event_type: str = Field(
        ..., description="Event type (FOUND, UPDATED, SKIPPED, ERROR)"
    )
    detail: str | None = None
    created_at: str | None = None

    @field_validator("event_type")
    @classmethod
    def validate_event_type(cls, v: str) -> str:
        """Validate event type."""
        valid_types = {"FOUND", "UPDATED", "SKIPPED", "ERROR"}
        if v not in valid_types:
            raise ValueError(f"Invalid event type. Must be one of: {valid_types}")
        return v
