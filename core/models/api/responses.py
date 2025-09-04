"""API response models."""

from pydantic import BaseModel, Field

from core.log import get_logger
from core.models.rows import (
    Paper,
    PaperBase,
    Summary,
    SummaryRead,
    UserStar,
)

logger = get_logger(__name__)


class PaperResponse(PaperBase, table=False):
    """Response model for paper details."""

    # Response-specific fields
    summary: Summary | None = None
    is_starred: bool = False
    is_read: bool = False

    @classmethod
    def from_crawler_paper(
        cls,
        paper: Paper,
        summary: Summary | None = None,
        is_starred: bool = False,
        is_read: bool = False,
    ) -> "PaperResponse":
        """Create PaperResponse from Paper (SQLModel)."""

        # Create base paper data from Paper model
        paper_data = paper.model_dump()
        return cls(
            summary=summary,
            is_starred=is_starred,
            is_read=is_read,
            **paper_data,
        )


class PaperListItemResponse(PaperBase, table=False):
    """Lightweight response model for paper list items with overview only."""

    # Lightweight fields for list view
    overview: str | None = None  # Uses existing summary.overview
    has_summary: bool = False  # Flag indicating if full summary exists
    relevance: int | None = None  # Relevance score for tags
    is_starred: bool = False
    is_read: bool = False

    @classmethod
    def from_paper_with_overview(
        cls,
        paper: Paper,
        overview: str | None = None,
        has_summary: bool = False,
        relevance: int | None = None,
        is_starred: bool = False,
        is_read: bool = False,
    ) -> "PaperListItemResponse":
        """Create PaperListItemResponse from Paper with overview."""
        paper_data = paper.model_dump()
        return cls(
            overview=overview,
            has_summary=has_summary,
            relevance=relevance,
            is_starred=is_starred,
            is_read=is_read,
            **paper_data,
        )

    @classmethod
    def from_paper_summary_row(
        cls,
        row: tuple[Paper, Summary | None],
    ) -> "PaperListItemResponse":
        """Create PaperListItemResponse from paper-summary joined query row.

        Args:
            row: Tuple containing (Paper, Summary)

        Returns:
            PaperListItemResponse with data from joined row
        """
        paper, summary = row

        # Extract data with type safety
        overview = summary.overview if summary else None
        relevance = summary.relevance if summary else None
        has_summary = summary is not None

        return cls.from_paper_with_overview(
            paper=paper,
            overview=overview,
            has_summary=has_summary,
            relevance=relevance,
            is_starred=False,
            is_read=False,
        )

    @classmethod
    def from_full_joined_row(
        cls,
        row: tuple[Paper, Summary | None, UserStar | None, SummaryRead | None],
    ) -> "PaperListItemResponse":
        """Create PaperListItemResponse from full joined query row with user status.

        Args:
            row: Tuple containing (Paper, Summary, UserStar, SummaryRead)

        Returns:
            PaperListItemResponse with data from joined row including user status
        """
        paper, summary, user_star, summary_read = row

        # Extract data with type safety
        overview = summary.overview if summary else None
        relevance = summary.relevance if summary else None
        has_summary = summary is not None
        is_starred = user_star is not None
        is_read = summary_read is not None

        return cls.from_paper_with_overview(
            paper=paper,
            overview=overview,
            has_summary=has_summary,
            relevance=relevance,
            is_starred=is_starred,
            is_read=is_read,
        )


class SummaryDetailResponse(BaseModel):
    """Response model for full summary details."""

    summary: Summary
    is_read: bool = False


class PaperListResponse(BaseModel):
    """Response model for paper list with pagination."""

    papers: list[PaperResponse] = Field(..., description="List of papers")
    total_count: int = Field(..., description="Total number of papers")
    limit: int = Field(..., description="Number of papers per page")
    offset: int = Field(..., description="Number of papers skipped")
    has_more: bool = Field(..., description="Whether there are more papers")


class PaperListLightweightResponse(BaseModel):
    """Lightweight response model for paper list with overview only."""

    papers: list[PaperListItemResponse] = Field(
        ..., description="List of papers with overview"
    )
    total_count: int = Field(..., description="Total number of papers")
    limit: int = Field(..., description="Number of papers per page")
    offset: int = Field(..., description="Number of papers skipped")
    has_more: bool = Field(..., description="Whether there are more papers")


class PaperDeleteResponse(BaseModel):
    """Response model for paper deletion."""

    success: bool
    message: str


class CategoriesResponse(BaseModel):
    """Response model for preset categories."""

    categories: list[str]
    count: int


class SummaryReadResponse(BaseModel):
    """Response model for marking summary as read."""

    success: bool
    message: str
    is_read: bool = True


class StarResponse(BaseModel):
    """Response model for star operations."""

    success: bool
    message: str
    is_starred: bool
    paper_id: int | None = None
    note: str | None = None

    @classmethod
    def success_response(cls, is_starred: bool, message: str) -> "StarResponse":
        """Create a successful StarResponse."""
        return cls(success=True, is_starred=is_starred, message=message)

    @classmethod
    def failure_response(cls, message: str) -> "StarResponse":
        """Create a failed StarResponse."""
        logger.error(f"Star operation failed: {message}")
        return cls(success=False, is_starred=False, message=message)


class StarredPapersResponse(BaseModel):
    """Response model for starred papers list with pagination."""

    papers: list[PaperResponse] = Field(..., description="List of starred papers")
    total_count: int = Field(..., description="Total number of starred papers")
    limit: int = Field(..., description="Number of papers per page")
    offset: int = Field(..., description="Number of papers skipped")
    has_more: bool = Field(..., description="Whether there are more papers")


class AuthError(BaseModel):
    """Model for authentication error."""

    detail: str = Field(..., description="Error detail")
    error: str = Field(..., description="Error type")
    environment: str = Field(..., description="Environment")


# Crawling response models
class CrawlCycleResult(BaseModel):
    """Result of a single crawl cycle."""

    papers_found: int = Field(description="Number of papers found")
    papers_stored: int = Field(description="Number of papers stored")
    category: str = Field(description="Category that was crawled")
    date: str = Field(description="Date that was crawled")


class CrawlerResponse(BaseModel):
    """Response model for crawler operations."""

    status: str
    message: str
    was_already_running: bool = False


class CrawlerStatusResponse(BaseModel):
    """Response model for crawler status."""

    is_running: bool
    is_active: bool
    current_date: str
    current_category_index: int
    categories: str


class CrawlerProgressResponse(BaseModel):
    """Response model for crawler progress."""

    total_papers_found: int
    total_papers_stored: int
    completed_date_categories: int
    failed_date_categories: int


class StatisticsResponse(BaseModel):
    """Response model for application statistics."""

    # Paper statistics
    total_papers: int = Field(description="Total number of papers stored in database")
    papers_with_summary: int = Field(description="Number of papers that have summaries")
    papers_without_summary: int = Field(
        description="Number of papers without summaries"
    )

    # Summary statistics
    batch_requested_summaries: int = Field(
        description="Number of summaries requested via batch processing"
    )

    # Processing statistics
    summary_coverage_percentage: float = Field(
        description="Percentage of papers that have summaries (0.0 to 100.0)"
    )

    # Timestamps
    last_updated: str = Field(description="When the statistics were last calculated")

    @classmethod
    def calculate_coverage_percentage(
        cls, papers_with_summary: int, total_papers: int
    ) -> float:
        """Calculate summary coverage percentage."""
        if total_papers == 0:
            return 0.0
        return round((papers_with_summary / total_papers) * 100, 2)

    @classmethod
    def create(
        cls,
        total_papers: int,
        papers_with_summary: int,
        batch_requested_summaries: int,
        last_updated: str,
    ) -> "StatisticsResponse":
        """Create StatisticsResponse with calculated fields."""
        papers_without_summary = total_papers - papers_with_summary
        summary_coverage_percentage = cls.calculate_coverage_percentage(
            papers_with_summary, total_papers
        )

        return cls(
            total_papers=total_papers,
            papers_with_summary=papers_with_summary,
            papers_without_summary=papers_without_summary,
            batch_requested_summaries=batch_requested_summaries,
            summary_coverage_percentage=summary_coverage_percentage,
            last_updated=last_updated,
        )
