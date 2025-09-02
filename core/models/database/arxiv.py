"""Database models for ArXiv exploration tracking."""

# TODO: This file is temporarily disabled due to missing FromTupleMixinBase
# from datetime import datetime
# from typing import TypeVar

# from pydantic import Field, field_validator

# from core.models.domain.arxiv import CrawlProgress

# from .entities import FromTupleMixinBase

# T = TypeVar("T", bound="ArxivCrawlProgress")


# class ArxivCrawlProgress(CrawlProgress, FromTupleMixinBase):
#     """Track crawl progress for ArXiv categories."""

#     @field_validator("category")
#     @classmethod
#     def validate_category(cls, v: str) -> str:
#         """Validate ArXiv category format."""
#         if not v or "." not in v:
#             raise ValueError("Invalid category format (e.g., cs.AI)")
#         return v

#     @field_validator("last_crawled_date", "last_historical_date")
#     @classmethod
#     def validate_date(cls, v: str) -> str:
#         """Validate date format (YYYY-MM-DD)."""
#         try:
#             datetime.strptime(v, "%Y-%m-%d")
#             return v
#         except ValueError:
#             raise ValueError("Invalid date format. Use YYYY-MM-DD")

#     @field_validator("created_at", "updated_at")
#     @classmethod
#     def validate_datetime(cls, v: str) -> str:
#         """Validate ISO8601 datetime format."""
#         try:
#             datetime.fromisoformat(v.replace("Z", "+00:00"))
#             return v
#         except ValueError:
#             raise ValueError("Invalid ISO8601 datetime format")


# class ArxivCompletedDay(FromTupleMixinBase):
#     """Track completed historical days per category."""

#     category: str = Field(..., description="ArXiv category")
#     completed_date: str = Field(..., description="Completed date")
#     created_at: str = Field(default_factory=lambda: datetime.now().isoformat())

#     @field_validator("category")
#     @classmethod
#     def validate_category(cls, v: str) -> str:
#         """Validate ArXiv category format."""
#         if not v or "." not in v:
#             raise ValueError("Invalid category format (e.g., cs.AI)")
#         return v

#     @field_validator("completed_date")
#     @classmethod
#     def validate_date(cls, v: str) -> str:
#         """Validate date format (YYYY-MM-DD)."""
#         try:
#             datetime.strptime(v, "%Y-%m-%d")
#             return v
#         except ValueError:
#             raise ValueError("Invalid date format. Use YYYY-MM-DD")

#     @field_validator("created_at")
#     @classmethod
#     def validate_datetime(cls, v: str) -> str:
#         """Validate ISO8601 datetime format."""
#         try:
#             datetime.fromisoformat(v.replace("Z", "+00:00"))
#             return v
#         except ValueError:
#             raise ValueError("Invalid ISO8601 datetime format")
