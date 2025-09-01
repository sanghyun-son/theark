"""Paper service for CRUD operations using new architecture."""

from sqlmodel import Session

from core import get_logger
from core.config import load_settings
from core.database.repository import (
    PaperRepository,
    SummaryRepository,
    UserStarRepository,
)
from core.database.repository.summary_read import SummaryReadRepository
from core.extractors import extractor_factory
from core.extractors.exceptions import ExtractionError
from core.llm.openai_client import UnifiedOpenAIClient
from core.models import (
    PaperCreateRequest,
    PaperDeleteResponse,
    PaperResponse,
    StarredPapersResponse,
    SummaryReadResponse,
)
from core.models.api.responses import (
    PaperListLightweightResponse,
    PaperListResponse,
    SummaryDetailResponse,
)
from core.models.rows import Paper, Summary
from core.services.summarization_service import PaperSummarizationService

logger = get_logger(__name__)


class PaperService:
    """Service for paper CRUD operations using new architecture."""

    def __init__(self) -> None:
        """Initialize paper service."""
        self.settings = load_settings()

    def _extract_arxiv_id(self, paper_data: PaperCreateRequest) -> str:
        """Extract arXiv ID from paper data."""
        if not paper_data.url:
            raise ValueError("No URL provided")

        try:
            extractor = extractor_factory.find_extractor_for_url(paper_data.url)
            return extractor.extract_identifier(paper_data.url)
        except Exception as e:
            raise ValueError(f"Invalid URL format: {e}")

    async def create_paper(
        self,
        paper_data: PaperCreateRequest,
        paper_repo: PaperRepository,
        summary_client: UnifiedOpenAIClient,
        skip_auto_summarization: bool = False,
    ) -> PaperResponse:
        """Create a new paper using new architecture."""
        arxiv_id = self._extract_arxiv_id(paper_data)

        # Check if paper already exists
        existing_paper = paper_repo.get_by_arxiv_id(arxiv_id)
        if existing_paper:
            logger.info(f"[{arxiv_id}] Already exists")
            return PaperResponse.from_crawler_paper(existing_paper)

        # Extract paper metadata using the new extractor system
        paper = await self._extract_paper(paper_data.url, arxiv_id, paper_repo)

        # Convert Paper to PaperResponse
        return PaperResponse.from_crawler_paper(paper)

    async def _extract_paper(
        self,
        url: str,
        arxiv_id: str,
        paper_repo: PaperRepository,
    ) -> Paper:
        """Extract paper metadata using the new extractor system."""
        try:
            extractor = extractor_factory.find_extractor_for_url(url)
            metadata = await extractor.extract_metadata_async(url)

            # Convert PaperMetadata to Paper (SQLModel)
            paper = Paper(
                arxiv_id=arxiv_id,
                title=metadata.title,
                abstract=metadata.abstract,
                authors=";".join(metadata.authors),
                primary_category=(
                    metadata.categories[0] if metadata.categories else "cs.AI"
                ),
                categories=",".join(metadata.categories),
                url_abs=metadata.url_abs,
                url_pdf=metadata.url_pdf,
                published_at=metadata.published_date,
            )

            # Save to database
            saved_paper = paper_repo.create(paper)

            logger.info(f"[{arxiv_id}] Extraction success")
            return saved_paper

        except ExtractionError as e:
            logger.error(f"[{arxiv_id}] Extraction failed: {e}")
            raise ValueError(f"Failed to extract paper {arxiv_id}: {e}")

    def _enrich_paper_response(
        self,
        paper: Paper,
        db_session: Session,
        user_id: int | None = None,
        summary: Summary | None = None,
        language: str | None = None,
    ) -> PaperResponse:
        """Enrich paper with user-specific data like star and read status."""
        is_starred = False
        is_read = False

        # Always fetch summary if language is provided and summary is not already provided
        if summary is None and language and paper.paper_id is not None:
            summary_repo = SummaryRepository(db_session)
            summary = summary_repo.get_by_paper_id_and_language(
                paper.paper_id, language
            )

        if user_id is not None and paper.paper_id is not None:
            # Use UserStarRepository directly to check if paper is starred
            star_repo = UserStarRepository(db_session)
            is_starred = star_repo.is_paper_starred(user_id, paper.paper_id)

            if summary and summary.summary_id:
                summary_read_repo = SummaryReadRepository(db_session)
                is_read = summary_read_repo.is_summary_read_by_user(
                    user_id, summary.summary_id
                )

        return PaperResponse.from_crawler_paper(
            paper,
            summary=summary,
            is_starred=is_starred,
            is_read=is_read,
        )

    async def get_paper(
        self,
        paper_identifier: str,
        db_session: Session,
        user_id: int | None = None,
        language: str = "English",
    ) -> PaperResponse:
        """Get a paper by ID or arXiv ID.

        This method uses the orchestration service to retrieve a single paper
        and enriches it with user-specific data (star/read status).

        Related method: get_papers() - for retrieving multiple papers
        """
        paper = self._get_paper_by_identifier(paper_identifier, db_session)
        if not paper:
            raise ValueError(f"Paper not found: {paper_identifier}")

        return self._enrich_paper_response(
            paper, db_session, user_id, language=language
        )

    def delete_paper(
        self,
        paper_identifier: str,
        db_session: Session,
    ) -> PaperDeleteResponse:
        """Delete a paper by ID or arXiv ID."""
        paper_repo = PaperRepository(db_session)
        paper = self._get_paper_by_identifier(paper_identifier, paper_repo.db)
        if not paper:
            raise ValueError("Paper not found")
        if paper.paper_id is None:
            raise ValueError("Paper has no ID")

        paper_repo.delete(paper.paper_id)
        return PaperDeleteResponse(
            success=True,
            message=f"Paper {paper_identifier} deleted successfully",
        )

    async def get_papers(
        self,
        db_session: Session,
        user_id: int | None = None,
        skip: int = 0,
        limit: int = 100,
        language: str | None = None,
    ) -> PaperListResponse:
        """Get a list of papers with optional filtering.

        This method retrieves multiple papers with pagination and enriches each
        with user-specific data (star/read status) using the same logic as get_paper().

        Related method: get_paper() - for retrieving a single paper
        """
        paper_repo = PaperRepository(db_session)
        papers = paper_repo.get_papers_with_summaries(
            skip=skip, limit=limit, language=language
        )

        # Use the same enrichment logic as get_paper for consistency
        paper_responses = [
            self._enrich_paper_response(paper, db_session, user_id, language=language)
            for paper in papers
        ]

        # Get total count for pagination
        total_count = paper_repo.get_total_count()
        has_more = (skip + limit) < total_count

        return PaperListResponse(
            papers=paper_responses,
            total_count=total_count,
            limit=limit,
            offset=skip,
            has_more=has_more,
        )

    async def get_papers_lightweight(
        self,
        db_session: Session,
        user_id: int | None = None,
        skip: int = 0,
        limit: int = 100,
        language: str | None = None,
    ) -> PaperListLightweightResponse:
        """Get a lightweight list of papers with overview only.

        This method retrieves papers with only overview for better performance.
        Full summaries are loaded on demand when user clicks on a paper.

        Args:
            db_session: Database session
            user_id: User ID for star/read status
            skip: Number of records to skip
            limit: Maximum number of records to return
            language: Language for summaries

        Returns:
            Lightweight paper list with overview only
        """
        paper_repo = PaperRepository(db_session)

        # Use optimized batch method if user_id is provided
        if user_id:
            paper_overview_data = paper_repo.get_papers_with_overview_optimized(
                skip=skip, limit=limit, language=language
            )

            # Create responses with user status
            paper_responses = []
            for overview_data in paper_overview_data:
                overview_data.is_starred = False
                overview_data.is_read = False
                paper_responses.append(overview_data)

            # Batch fetch user status for better performance
            if paper_responses:
                paper_ids = [
                    data.paper_id for data in paper_overview_data if data.paper_id
                ]

                # Batch fetch star status
                star_repo = UserStarRepository(db_session)
                starred_paper_ids = set(
                    star_repo.get_starred_paper_ids(user_id, paper_ids)
                )

                # Batch fetch read status
                summary_read_repo = SummaryReadRepository(db_session)
                summary_repo = SummaryRepository(db_session)

                summary_paper_ids = [
                    data.paper_id
                    for data in paper_overview_data
                    if data.paper_id and data.has_summary
                ]

                summaries = {}
                if summary_paper_ids:
                    summaries = summary_repo.get_by_paper_ids_and_language(
                        summary_paper_ids, language or "Korean"
                    )

                summary_ids = [s.summary_id for s in summaries.values() if s.summary_id]
                read_summary_ids = set()
                if summary_ids:
                    read_summary_ids = set(
                        summary_read_repo.get_read_summary_ids(user_id, summary_ids)
                    )

                # Update user status
                for i, overview_data in enumerate(paper_overview_data):
                    paper_id = overview_data.paper_id
                    is_starred = paper_id in starred_paper_ids if paper_id else False

                    is_read = False
                    if paper_id and overview_data.has_summary:
                        summary = summaries.get(paper_id)
                        if summary and summary.summary_id:
                            is_read = summary.summary_id in read_summary_ids

                    paper_responses[i].is_starred = is_starred
                    paper_responses[i].is_read = is_read
        else:
            # No user_id, use simple optimized method
            paper_overview_data = paper_repo.get_papers_with_overview_optimized(
                skip=skip, limit=limit, language=language
            )

            # Create responses without user-specific data
            paper_responses = []
            for overview_data in paper_overview_data:
                # overview_data is already a PaperListItemResponse, just set user status
                overview_data.is_starred = False
                overview_data.is_read = False
                paper_responses.append(overview_data)

        # Get total count for pagination
        total_count = paper_repo.get_total_count()
        has_more = (skip + limit) < total_count

        return PaperListLightweightResponse(
            papers=paper_responses,
            total_count=total_count,
            limit=limit,
            offset=skip,
            has_more=has_more,
        )

    async def get_paper_summary(
        self,
        paper_id: int,
        db_session: Session,
        user_id: int | None = None,
        language: str = "Korean",
    ) -> SummaryDetailResponse:
        """Get full summary for a specific paper on demand.

        Args:
            paper_id: Paper ID
            db_session: Database session
            user_id: User ID for read status
            language: Language for summary

        Returns:
            Full summary details with read status
        """
        # Get the full summary
        summarization_service = PaperSummarizationService()
        summary = await summarization_service.get_summary(
            paper_id, db_session, language
        )

        if not summary:
            raise ValueError(f"No summary found for paper {paper_id} in {language}")

        # Check read status
        is_read = False
        if user_id and summary.summary_id:
            summary_read_repo = SummaryReadRepository(db_session)
            is_read = summary_read_repo.is_summary_read_by_user(
                user_id, summary.summary_id
            )

        return SummaryDetailResponse(summary=summary, is_read=is_read)

    def _get_paper_by_identifier(
        self, paper_identifier: str, db_session: Session
    ) -> Paper | None:
        """Get a paper by ID or arXiv ID."""
        paper_repo = PaperRepository(db_session)

        # Try to parse as integer (paper ID)
        try:
            paper_id = int(paper_identifier)
            return paper_repo.get_by_id(paper_id)
        except ValueError:
            # Try as arXiv ID
            return paper_repo.get_by_arxiv_id(paper_identifier)

    async def get_starred_papers(
        self,
        user_id: int,
        db_session: Session,
        skip: int = 0,
        limit: int = 100,
        language: str = "English",
    ) -> StarredPapersResponse:
        """Get starred papers for a user."""
        star_repo = UserStarRepository(db_session)
        starred_papers = star_repo.get_starred_papers(user_id, skip=skip, limit=limit)

        paper_responses = [
            self._enrich_paper_response(paper, db_session, user_id, language=language)
            for paper in starred_papers
        ]

        # Get total count for pagination
        total_count = star_repo.get_starred_papers_count(user_id)
        has_more = (skip + limit) < total_count

        return StarredPapersResponse(
            papers=paper_responses,
            total_count=total_count,
            limit=limit,
            offset=skip,
            has_more=has_more,
        )

    async def mark_summary_as_read(
        self,
        paper_identifier: str,
        user_id: int,
        db_session: Session,
        language: str = "Korean",
    ) -> SummaryReadResponse:
        """Mark a summary as read for a user."""
        paper = self._get_paper_by_identifier(paper_identifier, db_session)
        if not paper:
            raise ValueError("Paper not found")

        if paper.paper_id is None:
            raise ValueError("Paper has no ID")

        summary_repo = SummaryRepository(db_session)
        summary = summary_repo.get_by_paper_id_and_language(paper.paper_id, language)
        if not summary:
            raise ValueError("Summary not found")

        summary_read_repo = SummaryReadRepository(db_session)
        if summary.summary_id is None:
            raise ValueError("Summary has no ID")
        success = summary_read_repo.mark_as_read(user_id, summary.summary_id)
        if not success:
            raise ValueError("Failed to mark summary as read")

        return SummaryReadResponse(
            success=True,
            message="Summary marked as read successfully",
        )
