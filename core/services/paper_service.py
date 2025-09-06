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
from core.extractors.exceptions import ExtractionError
from core.extractors.factory import find_extractor_for_url
from core.llm.openai_client import UnifiedOpenAIClient
from core.models import (
    PaperCreateRequest,
    PaperDeleteResponse,
    PaperResponse,
    StarredPapersResponse,
    SummaryReadResponse,
)
from core.models.api.responses import (
    PaperListItemResponse,
    PaperListLightweightResponse,
    PaperListResponse,
    SummaryDetailResponse,
)
from core.models.domain.paper_extraction import PaperMetadata
from core.models.rows import Paper, Summary
from core.services.summarization_service import PaperSummarizationService
from core.types import PaperSummaryStatus

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
            extractor = find_extractor_for_url(paper_data.url)
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
        # Early Exit: URL 검증
        if not url:
            raise ValueError("URL is required for paper extraction")

        # Early Exit: arXiv ID 검증
        if not arxiv_id:
            raise ValueError("arXiv ID is required for paper extraction")

        try:
            # Extractor 찾기 및 메타데이터 추출
            metadata = await self._extract_paper_metadata(url)

            # Paper 객체 생성 및 저장
            paper = self._create_paper_from_metadata(arxiv_id, metadata)
            saved_paper = paper_repo.create(paper)

            logger.info(f"[{arxiv_id}] Extraction success")
            return saved_paper

        except ExtractionError as e:
            logger.error(f"[{arxiv_id}] Extraction failed: {e}")
            raise ValueError(f"Failed to extract paper {arxiv_id}: {e}")

    async def _extract_paper_metadata(self, url: str) -> PaperMetadata:
        """Extract paper metadata from URL using appropriate extractor."""
        extractor = find_extractor_for_url(url)
        return await extractor.extract_metadata_async(url)

    def _create_paper_from_metadata(
        self, arxiv_id: str, metadata: PaperMetadata
    ) -> Paper:
        """Create Paper object from extracted metadata."""
        return Paper(
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

        # Early exit: Fetch summary if needed
        if summary is None and language and paper.paper_id is not None:
            summary_repo = SummaryRepository(db_session)
            summary = summary_repo.get_by_paper_id_and_language(
                paper.paper_id, language
            )

        # Early exit: No user ID or paper ID, return without user status
        if user_id is None or paper.paper_id is None:
            return PaperResponse.from_crawler_paper(
                paper,
                summary=summary,
                is_starred=is_starred,
                is_read=is_read,
            )

        # Get user star status
        star_repo = UserStarRepository(db_session)
        is_starred = star_repo.is_paper_starred(user_id, paper.paper_id)

        # Get user read status if summary exists
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
        language: str = "Korean",
        prioritize_summaries: bool = True,
        sort_by_relevance: bool = False,
        prioritize_starred: bool = False,
        prioritize_read: bool = False,
    ) -> PaperListResponse:
        """Get a list of papers with optional filtering.

        This method retrieves multiple papers with pagination and enriches each
        with user-specific data (star/read status) using the same logic as get_paper().

        Related method: get_paper() - for retrieving a single paper
        """
        # Use the unified method for all cases
        paper_repo = PaperRepository(db_session)
        papers = paper_repo.get_papers_with_user_priority(
            user_id=user_id or 0,  # Handle None case
            skip=skip,
            limit=limit,
            language=language,
            prioritize_summaries=prioritize_summaries,
            sort_by_relevance=sort_by_relevance,
            prioritize_starred=prioritize_starred,
            prioritize_read=prioritize_read,
        )

        # Convert Paper objects to PaperListItemResponse objects
        paper_overview_data = [
            PaperListItemResponse.model_validate(paper.model_dump()) for paper in papers
        ]

        if user_id:
            paper_responses = await self._enrich_papers_with_user_status(
                paper_overview_data, db_session, user_id, language
            )
        else:
            paper_responses = self._create_papers_without_user_status(
                paper_overview_data
            )

        # Convert PaperListItemResponse to PaperResponse
        paper_responses_full = []
        for paper_item in paper_responses:
            # Get the original paper object
            original_paper = next(
                (p for p in papers if p.paper_id == paper_item.paper_id), None
            )
            if original_paper:
                # Create full PaperResponse
                paper_response = self._enrich_paper_response(
                    original_paper, db_session, user_id, language=language
                )
                paper_response.is_starred = paper_item.is_starred
                paper_response.is_read = paper_item.is_read
                paper_responses_full.append(paper_response)

        total_count = paper_repo.get_total_count()
        has_more = (skip + limit) < total_count

        return PaperListResponse(
            papers=paper_responses_full,
            total_count=total_count,
            limit=limit,
            offset=skip,
            has_more=has_more,
        )

    async def get_papers_enhanced(
        self,
        db_session: Session,
        user_id: int | None = None,
        skip: int = 0,
        limit: int = 100,
        language: str = "Korean",
        prioritize_summaries: bool = False,
        sort_by_relevance: bool = False,
        categories: list[str] | None = None,
    ) -> PaperListResponse:
        """Get papers with enhanced sorting and filtering options.

        This method supports:
        - Summary status prioritization
        - Relevance-based sorting
        - Category filtering

        Args:
            db_session: Database session
            user_id: User ID for personalization
            skip: Number of records to skip
            limit: Maximum number of records to return
            language: Language for summaries
            prioritize_summaries: Whether to prioritize by summary status
            sort_by_relevance: Whether to sort by relevance score
            categories: List of categories to filter by

        Returns:
            Enhanced paper list with specified sorting and filtering
        """
        paper_repo = PaperRepository(db_session)
        papers = paper_repo.get_papers_with_summaries(
            skip=skip,
            limit=limit,
            language=language,
            prioritize_summaries=prioritize_summaries,
            sort_by_relevance=sort_by_relevance,
            categories=categories,
        )

        paper_responses = [
            self._enrich_paper_response(paper, db_session, user_id, language=language)
            for paper in papers
        ]

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
        language: str = "Korean",
        prioritize_summaries: bool = True,
        sort_by_relevance: bool = False,
        prioritize_starred: bool = False,
        prioritize_read: bool = False,
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
            prioritize_summaries: Whether to prioritize papers with summaries
            sort_by_relevance: Whether to sort papers by relevance score
            prioritize_starred: Whether to prioritize starred papers
            prioritize_read: Whether to prioritize read papers

        Returns:
            Lightweight paper list with overview only
        """
        paper_repo = PaperRepository(db_session)
        logger.debug(
            f"get_papers_lightweight called with: "
            f"prioritize_summaries={prioritize_summaries}, "
            f"sort_by_relevance={sort_by_relevance}, "
            f"prioritize_starred={prioritize_starred}, "
            f"prioritize_read={prioritize_read}"
        )

        # Use the unified method for all cases
        papers = paper_repo.get_papers_with_user_priority(
            user_id=user_id or 0,  # Handle None case
            skip=skip,
            limit=limit,
            language=language,
            prioritize_summaries=prioritize_summaries,
            sort_by_relevance=sort_by_relevance,
            prioritize_starred=prioritize_starred,
            prioritize_read=prioritize_read,
        )
        logger.debug(f"Repository returned {len(papers)} papers")
        if papers:
            logger.debug(f"First paper summary_status: {papers[0].summary_status}")

        # Get overview and relevance data for papers
        paper_ids = [paper.paper_id for paper in papers if paper.paper_id]
        overviews: dict[int, str] = {}
        relevances: dict[int, int] = {}
        if paper_ids:
            summary_repo = SummaryRepository(db_session)
            summaries_dict = summary_repo.get_by_paper_ids_and_language(
                paper_ids, language
            )
            overviews = {
                summary.paper_id: summary.overview
                for summary in summaries_dict.values()
                if summary.paper_id
            }
            relevances = {
                summary.paper_id: summary.relevance
                for summary in summaries_dict.values()
                if summary.paper_id
            }

        paper_overview_data: list[PaperListItemResponse] = []
        for paper in papers:
            if paper.paper_id is None:
                continue
            paper_data = PaperListItemResponse.model_validate(paper.model_dump())
            paper_data.overview = overviews.get(paper.paper_id)
            paper_data.relevance = relevances.get(paper.paper_id)
            paper_overview_data.append(paper_data)

        # Early exit: No user ID, create papers without user status
        if not user_id:
            paper_responses = self._create_papers_without_user_status(
                paper_overview_data
            )
            return self._build_lightweight_response(
                paper_responses, paper_repo, skip, limit
            )

        # User ID provided, enrich with user status
        paper_responses = await self._enrich_papers_with_user_status(
            paper_overview_data, db_session, user_id, language
        )
        return self._build_lightweight_response(
            paper_responses, paper_repo, skip, limit
        )

    async def _enrich_papers_with_user_status(
        self,
        paper_overview_data: list[PaperListItemResponse],
        db_session: Session,
        user_id: int,
        language: str = "Korean",
    ) -> list[PaperListItemResponse]:
        """Enrich papers with user-specific status (star/read).

        Args:
            paper_overview_data: List of paper overview data
            db_session: Database session
            user_id: User ID for status lookup
            language: Language for summaries

        Returns:
            List of papers enriched with user status
        """
        # Initialize responses with default user status
        paper_responses = []
        for overview_data in paper_overview_data:
            overview_data.is_starred = False
            overview_data.is_read = False
            # Set has_summary based on summary_status
            overview_data.has_summary = (
                overview_data.summary_status == PaperSummaryStatus.DONE
            )
            paper_responses.append(overview_data)

        # Early exit: No papers to process
        if not paper_responses:
            return paper_responses

        # Batch fetch user status for better performance
        paper_ids = [data.paper_id for data in paper_overview_data if data.paper_id]

        # Get star status
        starred_paper_ids = self._batch_fetch_user_star_status(
            db_session, user_id, paper_ids
        )

        # Get read status
        read_summary_ids = self._batch_fetch_user_read_status(
            db_session, user_id, paper_overview_data, language
        )

        # Update user status
        self._update_paper_user_status(
            paper_responses, paper_overview_data, starred_paper_ids, read_summary_ids
        )

        return paper_responses

    def _create_papers_without_user_status(
        self, paper_overview_data: list[PaperListItemResponse]
    ) -> list[PaperListItemResponse]:
        """Create paper responses without user-specific data.

        Args:
            paper_overview_data: List of paper overview data

        Returns:
            List of papers with default user status
        """
        paper_responses = []
        for overview_data in paper_overview_data:
            overview_data.is_starred = False
            overview_data.is_read = False
            # Set has_summary based on summary_status
            overview_data.has_summary = (
                overview_data.summary_status == PaperSummaryStatus.DONE
            )
            paper_responses.append(overview_data)
        return paper_responses

    def _batch_fetch_user_star_status(
        self, db_session: Session, user_id: int, paper_ids: list[int]
    ) -> set[int]:
        """Batch fetch star status for multiple papers.

        Args:
            db_session: Database session
            user_id: User ID
            paper_ids: List of paper IDs

        Returns:
            Set of starred paper IDs
        """
        if not paper_ids:
            return set()

        star_repo = UserStarRepository(db_session)
        return set(star_repo.get_starred_paper_ids(user_id, paper_ids))

    def _batch_fetch_user_read_status(
        self,
        db_session: Session,
        user_id: int,
        paper_overview_data: list[PaperListItemResponse],
        language: str = "Korean",
    ) -> dict[int, int]:
        """Batch fetch read status for multiple papers.

        Args:
            db_session: Database session
            user_id: User ID
            paper_overview_data: List of paper overview data
            language: Language for summaries

        Returns:
            Dictionary mapping paper_id to summary_id for read summaries
        """
        summary_paper_ids = [
            data.paper_id
            for data in paper_overview_data
            if data.paper_id and data.has_summary
        ]

        if not summary_paper_ids:
            return {}

        # Get summaries for these papers
        summary_repo = SummaryRepository(db_session)
        summaries_dict = summary_repo.get_by_paper_ids_and_language(
            summary_paper_ids, language
        )

        if not summaries_dict:
            return {}

        # Get summary IDs
        summary_ids: list[int] = []
        for summary in summaries_dict.values():
            if summary.summary_id is not None:
                summary_ids.append(summary.summary_id)
        if not summary_ids:
            return {}

        # Batch fetch read status
        summary_read_repo = SummaryReadRepository(db_session)
        read_summary_ids = summary_read_repo.get_read_summary_ids(user_id, summary_ids)

        # Create mapping from paper_id to summary_id for read summaries
        read_summary_mapping = {}
        for summary in summaries_dict.values():
            if summary.summary_id in read_summary_ids and summary.paper_id:
                read_summary_mapping[summary.paper_id] = summary.summary_id

        return read_summary_mapping

    def _update_paper_user_status(
        self,
        paper_responses: list[PaperListItemResponse],
        paper_overview_data: list[PaperListItemResponse],
        starred_paper_ids: set[int],
        read_summary_mapping: dict[int, int],
    ) -> None:
        """Update papers with user status data.

        Args:
            paper_responses: List of paper responses to update
            paper_overview_data: Original paper overview data
            starred_paper_ids: Set of starred paper IDs
            read_summary_mapping: Dictionary mapping paper_id to summary_id for read summaries
        """
        for i, overview_data in enumerate(paper_overview_data):
            paper_id = overview_data.paper_id
            is_starred = paper_id in starred_paper_ids if paper_id else False

            is_read = False
            if paper_id and overview_data.has_summary:
                # Check if this paper's summary has been read
                is_read = paper_id in read_summary_mapping

            paper_responses[i].is_starred = is_starred
            paper_responses[i].is_read = is_read

    def _build_lightweight_response(
        self,
        paper_responses: list[PaperListItemResponse],
        paper_repo: PaperRepository,
        skip: int,
        limit: int,
    ) -> PaperListLightweightResponse:
        """Build the final lightweight response.

        Args:
            paper_responses: List of enriched paper responses
            paper_repo: Paper repository for total count
            skip: Number of records skipped
            limit: Number of records requested

        Returns:
            Complete lightweight response
        """
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

        # Early exit: No user ID or summary ID, return without read status
        is_read = False
        if not user_id or not summary.summary_id:
            return SummaryDetailResponse(summary=summary, is_read=is_read)

        # Check read status
        summary_read_repo = SummaryReadRepository(db_session)
        is_read = summary_read_repo.is_summary_read_by_user(user_id, summary.summary_id)

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

        if summary.summary_id is None:
            raise ValueError("Summary has no ID")

        summary_read_repo = SummaryReadRepository(db_session)
        success = summary_read_repo.mark_as_read(user_id, summary.summary_id)
        if not success:
            raise ValueError("Failed to mark summary as read")

        return SummaryReadResponse(
            success=True,
            message="Summary marked as read successfully",
        )
