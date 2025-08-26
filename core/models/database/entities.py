"""Database entity models that map directly to database tables."""

from datetime import datetime
from typing import Any

from pydantic import BaseModel, Field, field_validator


class PaperEntity(BaseModel):
    """Paper database entity model."""

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

    @classmethod
    def from_tuple(cls, row: tuple[Any, ...]) -> "PaperEntity":
        """Create PaperEntity from database tuple row."""
        return cls(
            paper_id=row[0],
            arxiv_id=row[1],
            title=row[2],
            authors=row[3],
            abstract=row[4],
            primary_category=row[5].split(".")[0],
            categories=row[5],
            published_at=row[6],
            updated_at=row[7],
            url_abs=row[8],
            url_pdf=row[9],
        )


class SummaryEntity(BaseModel):
    """Summary database entity model."""

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
    is_read: bool = Field(
        default=False, description="Whether the summary has been read"
    )
    created_at: str | None = None

    @field_validator("language")
    @classmethod
    def validate_language(cls, v: str) -> str:
        """Validate summary language."""
        valid_languages = {"Korean", "English"}
        if v not in valid_languages:
            raise ValueError(f"Invalid language. Must be one of: {valid_languages}")
        return v

    @classmethod
    def from_tuple(cls, row: tuple[Any, ...]) -> "SummaryEntity":
        """Create SummaryEntity from database tuple row."""
        return cls(
            summary_id=row[0],
            paper_id=row[1],
            version=row[2],
            overview=row[3],
            motivation=row[4],
            method=row[5],
            result=row[6],
            conclusion=row[7],
            language=row[8],
            interests=row[9],
            relevance=row[10],
            model=row[11],
            is_read=bool(row[12]),
            created_at=row[13],
        )


class UserEntity(BaseModel):
    """User database entity model."""

    user_id: int = Field(..., gt=0)
    email: str = Field(..., description="User email address")
    display_name: str | None = None

    @field_validator("email")
    @classmethod
    def validate_email(cls, v: str) -> str:
        """Validate email format."""
        if "@" not in v or "." not in v:
            raise ValueError("Invalid email format")
        return v.lower()

    @classmethod
    def from_tuple(cls, row: tuple[Any, ...]) -> "UserEntity":
        """Create UserEntity from database tuple row."""
        return cls(
            user_id=row[0],
            email=row[1],
            display_name=row[2],
        )


class UserInterestEntity(BaseModel):
    """User interest database entity model."""

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

    @classmethod
    def from_tuple(cls, row: tuple[Any, ...]) -> "UserInterestEntity":
        """Create UserInterestEntity from database tuple row."""
        return cls(
            user_id=row[0],
            kind=row[1],
            value=row[2],
            weight=row[3],
        )


class UserStarEntity(BaseModel):
    """User star/bookmark database entity model."""

    user_id: int = Field(..., gt=0)
    paper_id: int = Field(..., gt=0)
    note: str | None = None
    created_at: str | None = None

    @classmethod
    def from_tuple(cls, row: tuple[Any, ...]) -> "UserStarEntity":
        """Create UserStarEntity from database tuple row."""
        return cls(
            user_id=row[0],
            paper_id=row[1],
            note=row[2],
            created_at=row[3],
        )


class FeedItem(BaseModel):
    """Feed item database entity model."""

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

    @classmethod
    def from_tuple(cls, row: tuple[Any, ...]) -> "FeedItem":
        """Create FeedItem from database tuple row."""
        return cls(
            feed_item_id=row[0],
            user_id=row[1],
            paper_id=row[2],
            score=row[3],
            feed_date=row[4],
            created_at=row[5],
        )


class CrawlEvent(BaseModel):
    """Crawl event database entity model."""

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

    @classmethod
    def from_tuple(cls, row: tuple[Any, ...]) -> "CrawlEvent":
        """Create CrawlEvent from database tuple row."""
        return cls(
            event_id=row[0],
            arxiv_id=row[1],
            event_type=row[2],
            detail=row[3],
            created_at=row[4],
        )
