"""Domain models for ArXiv exploration."""

from datetime import datetime

from pydantic import BaseModel, Field

from core.models.domain.paper_extraction import PaperMetadata


class ArxivPaper(PaperMetadata):
    """ArXiv paper domain model."""

    arxiv_id: str = Field(..., description="ArXiv ID (e.g., 1706.03762)")
    primary_category: str = Field(..., description="Primary ArXiv category")


class CrawlProgress(BaseModel):
    """Crawl progress domain model."""

    category: str = Field(..., description="ArXiv category (e.g., cs.AI)")
    last_crawled_date: str = Field(..., description="Last crawled date for new papers")
    last_crawled_index: int = Field(
        default=0, description="Last crawled index for new papers"
    )
    last_historical_date: str = Field(
        ..., description="Last historical date being crawled"
    )
    last_historical_index: int = Field(
        default=0, description="Last historical index being crawled"
    )
    is_active: bool = Field(default=True, description="Whether this category is active")
    created_at: str = Field(default_factory=lambda: datetime.now().isoformat())
    updated_at: str = Field(default_factory=lambda: datetime.now().isoformat())


class CompletedDay(BaseModel):
    """Completed day domain model."""

    category: str = Field(..., description="ArXiv category")
    completed_date: str = Field(..., description="Completed date")
    created_at: str = Field(default_factory=lambda: datetime.now().isoformat())
