"""SQLModel database models for TheArk."""

from sqlmodel import Field, Index, Relationship, SQLModel

from core.types import PaperSummaryStatus
from core.utils import get_current_timestamp


class PaperBase(SQLModel):
    """Base paper model with common fields."""

    paper_id: int | None = Field(default=None, primary_key=True)
    arxiv_id: str = Field(
        unique=True, index=True, description="arXiv ID (e.g., 2101.00001)"
    )
    latest_version: int = Field(default=1, ge=1)
    title: str = Field(description="Paper title")
    abstract: str = Field(description="Paper abstract")
    primary_category: str = Field(description="Primary category (e.g., cs.CL)")
    categories: str = Field(description="Comma-separated categories")
    authors: str = Field(description="Semicolon-separated authors")
    url_abs: str = Field(description="Abstract URL")
    url_pdf: str | None = Field(default=None, description="PDF URL")
    published_at: str = Field(description="ISO8601 datetime")
    updated_at: str = Field(
        default_factory=get_current_timestamp,
        description="ISO8601 datetime - automatically updated",
    )
    summary_status: PaperSummaryStatus = Field(
        default=PaperSummaryStatus.BATCHED,
        description="Summary status: batched, processing, done",
    )


class Paper(PaperBase, table=True):
    """Paper database model using SQLModel."""

    # Performance indexes
    __table_args__ = (
        Index("idx_paper_updated_at", "updated_at"),  # For ORDER BY updated_at DESC
        Index("idx_paper_summary_status", "summary_status"),  # For filtering by status
    )

    # Relationship attributes
    summaries: list["Summary"] = Relationship(back_populates="paper")
    user_stars: list["UserStar"] = Relationship(back_populates="paper")


class Summary(SQLModel, table=True):
    """Summary database model using SQLModel."""

    summary_id: int | None = Field(default=None, primary_key=True)
    paper_id: int | None = Field(foreign_key="paper.paper_id")
    version: str = Field(description="Summary version")
    overview: str = Field(description="Summary overview")
    motivation: str = Field(description="Research motivation")
    method: str = Field(description="Research method")
    result: str = Field(description="Research results")
    conclusion: str = Field(description="Research conclusion")
    language: str = Field(description="Summary language")
    interests: str = Field(description="Comma-separated interests")
    relevance: int = Field(ge=1, le=10, description="Relevance score (1-10)")
    model: str | None = Field(default=None, description="LLM model used")
    updated_at: str = Field(
        default_factory=get_current_timestamp,
        description="ISO8601 datetime - automatically updated",
    )

    # Performance indexes
    __table_args__ = (
        Index("idx_summary_paper_id", "paper_id"),  # For JOINs with paper table
        Index("idx_summary_language", "language"),  # For language filtering
        Index("idx_summary_relevance", "relevance"),  # For relevance-based sorting
    )

    # Relationship attributes
    paper: Paper = Relationship(back_populates="summaries")
    summary_reads: list["SummaryRead"] = Relationship(back_populates="summary")


class SummaryRead(SQLModel, table=True):
    """Summary read status for users."""

    read_id: int | None = Field(default=None, primary_key=True)
    user_id: int = Field(foreign_key="user.user_id")
    summary_id: int = Field(foreign_key="summary.summary_id")
    read_at: str = Field(description="ISO8601 datetime when summary was read")

    # Performance indexes
    __table_args__ = (
        Index(
            "idx_summaryread_user_summary", "user_id", "summary_id"
        ),  # For user status queries
    )

    # Relationship attributes
    summary: Summary = Relationship(back_populates="summary_reads")
    user: "User" = Relationship(back_populates="summary_reads")


class User(SQLModel, table=True):
    """User database model using SQLModel."""

    user_id: int | None = Field(default=None, primary_key=True)
    email: str = Field(unique=True, index=True, description="User email")
    display_name: str | None = Field(default=None, description="User display name")

    # Relationship attributes
    user_stars: list["UserStar"] = Relationship(back_populates="user")
    summary_reads: list[SummaryRead] = Relationship(back_populates="user")
    user_interests: list["UserInterest"] = Relationship(back_populates="user")


class UserInterest(SQLModel, table=True):
    """User interest database model using SQLModel."""

    interest_id: int | None = Field(default=None, primary_key=True)
    user_id: int = Field(foreign_key="user.user_id")
    category: str = Field(description="Interest category")
    weight: int = Field(default=1, ge=1, le=10, description="Interest weight (1-10)")

    # Relationship attributes
    user: User = Relationship(back_populates="user_interests")


class UserStar(SQLModel, table=True):
    """User star database model using SQLModel."""

    star_id: int | None = Field(default=None, primary_key=True)
    user_id: int = Field(foreign_key="user.user_id")
    paper_id: int = Field(foreign_key="paper.paper_id")
    note: str | None = Field(default=None, description="User note for the star")

    # Performance indexes
    __table_args__ = (
        Index(
            "idx_userstar_user_paper", "user_id", "paper_id"
        ),  # For user status queries
    )

    # Relationship attributes
    user: User = Relationship(back_populates="user_stars")
    paper: Paper = Relationship(back_populates="user_stars")


class LLMRequest(SQLModel, table=True):
    """LLM request tracking database model using SQLModel."""

    request_id: int | None = Field(default=None, primary_key=True)
    timestamp: str = Field(description="ISO timestamp of the request")
    model: str = Field(description="LLM model used (e.g., gpt-4o-mini)")
    provider: str = Field(
        default="openai", description="LLM provider (openai, anthropic, etc.)"
    )
    endpoint: str = Field(
        default="/v1/chat/completions", description="API endpoint called"
    )
    is_batched: bool = Field(
        default=False, description="Whether this was a batch request"
    )
    prompt_tokens: int | None = Field(default=None, description="Tokens in the prompt")
    completion_tokens: int | None = Field(
        default=None, description="Tokens in the completion"
    )
    total_tokens: int | None = Field(default=None, description="Total tokens used")
    response_time_ms: int | None = Field(
        default=None, description="Response time in milliseconds"
    )
    status: str = Field(
        default="pending", description="Request status (pending, success, error)"
    )
    error_message: str | None = Field(
        default=None, description="Error message if failed"
    )
    http_status_code: int | None = Field(default=None, description="HTTP status code")
    estimated_cost_usd: float | None = Field(
        default=None, description="Estimated cost in USD"
    )


class LLMBatchRequest(SQLModel, table=True):
    """LLM batch request database model using SQLModel."""

    batch_id: str = Field(primary_key=True, description="OpenAI batch ID")
    status: str = Field(default="pending", description="Batch status")
    entity_count: int = Field(description="Number of entities in this batch")
    input_file_id: str | None = Field(default=None, description="Input file ID")
    error_file_id: str | None = Field(default=None, description="Error file ID")
    created_at: str = Field(description="ISO timestamp when batch was created")
    completed_at: str | None = Field(
        default=None, description="ISO timestamp when batch completed"
    )
    # Batch completion metrics
    successful_count: int = Field(
        default=0, description="Number of successfully processed results"
    )
    failed_count: int = Field(default=0, description="Number of failed results")


class ArxivFailedPaper(SQLModel, table=True):
    """ArXiv failed paper tracking database model using SQLModel."""

    failed_id: int | None = Field(default=None, primary_key=True)
    arxiv_id: str = Field(description="ArXiv ID (e.g., 2101.00001)")
    category: str = Field(description="ArXiv category (e.g., cs.AI)")
    error_message: str = Field(description="Error message from failed processing")
    retry_count: int = Field(default=0, description="Number of retry attempts made")
    last_retry_at: str | None = Field(
        default=None, description="ISO8601 datetime of last retry attempt"
    )
    created_at: str = Field(
        default_factory=get_current_timestamp,
        description="ISO8601 datetime - automatically updated",
    )
    updated_at: str = Field(
        default_factory=get_current_timestamp,
        description="ISO8601 datetime - automatically updated",
    )


class CrawlCompletion(SQLModel, table=True):
    """Crawl completion status for date-category combinations."""

    completion_id: int | None = Field(default=None, primary_key=True)
    category: str = Field(description="ArXiv category (e.g., cs.AI)")
    date: str = Field(description="Date in YYYY-MM-DD format")
    papers_found: int = Field(default=0, description="Number of papers found")
    papers_stored: int = Field(default=0, description="Number of papers stored")
    completed_at: str = Field(
        default_factory=get_current_timestamp,
        description="ISO8601 datetime when crawl was completed",
    )
