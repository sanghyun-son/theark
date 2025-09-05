"""Query builders for paper repository operations."""

from __future__ import annotations

from sqlalchemy import Label, case, or_
from sqlmodel import Session, desc, select
from sqlmodel.sql._expression_select_cls import Select, SelectOfScalar

from core.models.rows import Paper, Summary, SummaryRead, UserStar
from core.types import PaperSummaryStatus


class PaperQueryBuilder:
    """Builder for paper queries with different sorting and filtering options."""

    def __init__(self, db_session: Session) -> None:
        self.db = db_session

    def _build_priority_case(self) -> Label[int]:
        """Build priority case for summary status ordering."""
        return case(
            (Paper.summary_status == PaperSummaryStatus.DONE, 1),  # type: ignore[arg-type]
            (Paper.summary_status == PaperSummaryStatus.PROCESSING, 2),  # type: ignore[arg-type]
            (Paper.summary_status == PaperSummaryStatus.ERROR, 3),  # type: ignore[arg-type]
            (Paper.summary_status == PaperSummaryStatus.BATCHED, 4),  # type: ignore[arg-type]
            else_=5,  # Papers with no summary status
        ).label("priority")

    def build_simple_query(
        self,
        skip: int = 0,
        limit: int = 100,
        categories: list[str] | None = None,
    ) -> SelectOfScalar[Paper]:
        """Build simple query with basic filtering and timestamp sorting.

        Args:
            skip: Number of records to skip
            limit: Maximum number of records to return
            categories: List of categories to filter by

        Returns:
            SQLAlchemy query for Paper objects
        """
        query = select(Paper)

        # Apply category filtering
        if categories:
            category_conditions = [
                Paper.categories.like(f"%{category}%")  # type: ignore[attr-defined]
                for category in categories
            ]
            query = query.where(or_(*category_conditions))

        return query.order_by(desc(Paper.updated_at)).offset(skip).limit(limit)

    def build_priority_query(
        self,
        skip: int = 0,
        limit: int = 100,
        categories: list[str] | None = None,
    ) -> SelectOfScalar[Paper]:
        """Build query with summary status priority sorting.

        Args:
            skip: Number of records to skip
            limit: Maximum number of records to return
            categories: List of categories to filter by

        Returns:
            SQLAlchemy query for Paper objects
        """
        query = select(Paper)

        # Apply category filtering
        if categories:
            category_conditions = [
                Paper.categories.like(f"%{category}%")  # type: ignore[attr-defined]
                for category in categories
            ]
            query = query.where(or_(*category_conditions))

        return self._build_summary_priority_query(query, skip, limit)

    def build_relevance_query(
        self,
        skip: int = 0,
        limit: int = 100,
        categories: list[str] | None = None,
        language: str = "Korean",
    ) -> Select[tuple[Paper, float]]:
        """Build query with relevance-based sorting.

        Args:
            skip: Number of records to skip
            limit: Maximum number of records to return
            categories: List of categories to filter by
            language: Language for summaries

        Returns:
            SQLAlchemy query for (Paper, relevance_score) tuples
        """
        query = select(Paper)

        # Apply category filtering
        if categories:
            category_conditions = [
                Paper.categories.like(f"%{category}%")  # type: ignore[attr-defined]
                for category in categories
            ]
            query = query.where(or_(*category_conditions))

        return self._build_relevance_sorting_query(query, skip, limit, language)

    def build_combined_query(
        self,
        skip: int = 0,
        limit: int = 100,
        categories: list[str] | None = None,
        language: str = "Korean",
    ) -> Select[tuple[Paper, float]]:
        """Build query with combined priority and relevance sorting.

        Args:
            skip: Number of records to skip
            limit: Maximum number of records to return
            categories: List of categories to filter by
            language: Language for summaries

        Returns:
            SQLAlchemy query for (Paper, relevance_score) tuples
        """
        query = select(Paper)

        # Apply category filtering
        if categories:
            category_conditions = [
                Paper.categories.like(f"%{category}%")  # type: ignore[attr-defined]
                for category in categories
            ]
            query = query.where(or_(*category_conditions))

        return self._build_combined_sorting_query(query, skip, limit, language)

    def _build_combined_sorting_query(
        self,
        base_query: SelectOfScalar[Paper],
        skip: int,
        limit: int,
        language: str = "Korean",
    ) -> Select[tuple[Paper, float]]:
        """Build query with combined priority and relevance sorting."""

        priority_case = self._build_priority_case()

        relevance_case = case(
            (Summary.relevance.is_not(None), Summary.relevance),  # type: ignore[attr-defined]
            else_=0.0,
        ).label("relevance")

        query = (
            select(Paper, relevance_case)
            .join(Summary, isouter=True)
            .where(Summary.language == language)
            .order_by(
                priority_case.asc(),  # Lower priority number = higher priority
                relevance_case.desc(),  # Higher relevance = better
                desc(Paper.updated_at),  # Newer papers first
            )
            .offset(skip)
            .limit(limit)
        )

        return query

    def _build_summary_priority_query(
        self,
        base_query: SelectOfScalar[Paper],
        skip: int,
        limit: int,
    ) -> SelectOfScalar[Paper]:
        """Build query with summary status priority sorting."""
        priority_case = self._build_priority_case()

        return (
            base_query.order_by(
                priority_case.asc(),  # Lower priority number = higher priority
                desc(Paper.updated_at),  # Newer papers first
            )
            .offset(skip)
            .limit(limit)
        )

    def _build_relevance_sorting_query(
        self,
        base_query: SelectOfScalar[Paper],
        skip: int,
        limit: int,
        language: str = "Korean",
    ) -> Select[tuple[Paper, float]]:
        """Build query with relevance-based sorting."""
        relevance_case = case(
            (Summary.relevance.is_not(None), Summary.relevance),  # type: ignore[attr-defined]
            else_=0.0,
        ).label("relevance")

        query = (
            select(Paper, relevance_case)
            .join(Summary, isouter=True)
            .where(Summary.language == language)
            .order_by(
                relevance_case.desc(),  # Higher relevance = better
                desc(Paper.updated_at),  # Newer papers first
            )
            .offset(skip)
            .limit(limit)
        )

        return query


class PaperJoinQueryBuilder:
    """Builder for paper queries with JOINs to related tables."""

    def __init__(self, db_session: Session) -> None:
        self.db = db_session

    def build_papers_with_summaries_join(
        self,
        skip: int = 0,
        limit: int = 100,
        language: str = "Korean",
    ) -> Select[tuple[Paper, Summary]]:
        """Build query for papers with summaries using JOIN."""
        statement = (
            select(Paper, Summary)
            .join(Summary, isouter=True)
            .where(Summary.language == language)
            .order_by(desc(Paper.updated_at))
            .offset(skip)
            .limit(limit)
        )
        return statement

    def build_papers_with_user_status_join(
        self,
        skip: int = 0,
        limit: int = 100,
        language: str = "Korean",
    ) -> Select[tuple[Paper, Summary, UserStar, SummaryRead]]:
        """Build query for papers with user status using JOIN."""

        # Build the base query with multiple JOINs
        statement = (
            select(Paper, Summary, UserStar, SummaryRead)
            .join(Summary, isouter=True)
            .join(UserStar, isouter=True)
            .join(SummaryRead, isouter=True)
            .where(Summary.language == language)
            .order_by(desc(Paper.updated_at))
            .offset(skip)
            .limit(limit)
        )
        return statement
