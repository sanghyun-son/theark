"""Statistics service for application metrics."""

from datetime import datetime

from sqlalchemy import func
from sqlmodel import Session, select

from core.log import get_logger
from core.models.api.responses import StatisticsResponse
from core.models.rows import Paper, Summary

logger = get_logger(__name__)


class StatisticsService:
    """Service for calculating application statistics."""

    def __init__(self, db: Session) -> None:
        """Initialize statistics service with database session."""
        self.db = db

    def get_application_statistics(self) -> StatisticsResponse:
        """Get comprehensive application statistics.

        Returns:
            StatisticsResponse with paper and summary counts
        """
        # Count total papers using SQLAlchemy 2.0 style
        total_papers_result = self.db.exec(
            select(func.count()).select_from(Paper)
        ).first()
        total_papers = total_papers_result or 0

        # Count papers with summaries using EXISTS subquery
        papers_with_summary_result = self.db.exec(
            select(func.count())
            .select_from(Paper)
            .where(
                select(Summary.paper_id)
                .where(Summary.paper_id == Paper.paper_id)
                .exists()
            )
        ).first()
        papers_with_summary = papers_with_summary_result or 0

        # Count batch requested summaries (using summary_status)
        # Note: This assumes there's a way to identify batch-requested summaries
        # For now, we'll count all summaries as a placeholder
        batch_requested_summaries = papers_with_summary

        # Generate timestamp
        last_updated = datetime.now().isoformat()

        return StatisticsResponse.create(
            total_papers=total_papers,
            papers_with_summary=papers_with_summary,
            batch_requested_summaries=batch_requested_summaries,
            last_updated=last_updated,
        )
