"""Paper service for CRUD operations using new architecture."""

from sqlmodel import Session

from core import get_logger
from core.config import load_settings
from core.database.repository import (
    PaperRepository,
    SummaryRepository,
    UserRepository,
    UserStarRepository,
)
from core.database.repository.summary_read import SummaryReadRepository
from core.llm.openai_client import UnifiedOpenAIClient
from core.models import (
    PaperCreateRequest,
    PaperDeleteResponse,
    PaperResponse,
    StarredPapersResponse,
    StarResponse,
    SummaryReadResponse,
)
from core.models.api.responses import PaperListResponse
from core.models.rows import Paper
from core.services.paper_orchestration_service import PaperOrchestrationService

logger = get_logger(__name__)


class PaperService:
    """Service for paper CRUD operations using new architecture."""

    def __init__(self) -> None:
        """Initialize paper service."""
        self.settings = load_settings()
        self.orchestration_service = PaperOrchestrationService()

    async def create_paper(
        self,
        paper_data: PaperCreateRequest,
        paper_repo: PaperRepository,
        summary_client: UnifiedOpenAIClient,
        skip_auto_summarization: bool = False,
    ) -> PaperResponse:
        """Create a new paper using new architecture."""
        if skip_auto_summarization:
            paper = await self.orchestration_service.create_paper_streaming(
                paper_data,
                paper_repo,
            )
        else:
            paper = await self.orchestration_service.create_paper_normal(
                paper_data,
                paper_repo,
                summary_client,
            )

        # Convert Paper to PaperResponse
        return PaperResponse.from_crawler_paper(paper)

    async def get_paper(
        self,
        paper_identifier: str,
        db_session: Session,
        user_id: int | None = None,
    ) -> PaperResponse:
        """Get a paper by ID or arXiv ID."""
        paper = await self.orchestration_service.get_paper(paper_identifier, db_session)

        # Check if user has starred this paper
        is_starred = False
        if user_id is not None and paper.paper_id is not None:
            star_repo = UserStarRepository(db_session)
            is_starred = star_repo.is_paper_starred(user_id, paper.paper_id)

        # Check if user has read the summary
        is_read = False
        if user_id is not None and paper.paper_id is not None:
            summary_repo = SummaryRepository(db_session)
            summary = summary_repo.get_by_paper_id_and_language(
                paper.paper_id, "English"
            )
            if summary and summary.summary_id:
                summary_read_repo = SummaryReadRepository(db_session)
                is_read = summary_read_repo.is_summary_read_by_user(
                    user_id, summary.summary_id
                )

        # Convert Paper to PaperResponse
        return PaperResponse.from_crawler_paper(
            paper,
            is_starred=is_starred,
            is_read=is_read,
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
        """Get a list of papers with optional filtering."""
        paper_repo = PaperRepository(db_session)
        papers = paper_repo.get_papers_with_summaries(
            skip=skip, limit=limit, language=language
        )

        # Convert Paper objects to PaperResponse objects
        paper_responses = []
        for paper in papers:
            # Get summary for the paper if language is specified
            summary = None
            if language and paper.paper_id is not None:
                summary_repo = SummaryRepository(db_session)
                summary = summary_repo.get_by_paper_id_and_language(
                    paper.paper_id, language
                )

            # Check if user has starred this paper
            is_starred = False
            if user_id is not None and paper.paper_id is not None:
                star_repo = UserStarRepository(db_session)
                is_starred = star_repo.is_paper_starred(user_id, paper.paper_id)

            # Check if user has read the summary
            is_read = False
            if (
                user_id is not None
                and paper.paper_id is not None
                and summary
                and summary.summary_id
            ):
                summary_read_repo = SummaryReadRepository(db_session)
                is_read = summary_read_repo.is_summary_read_by_user(
                    user_id, summary.summary_id
                )

            paper_response = PaperResponse.from_crawler_paper(
                paper,
                summary=summary,
                is_starred=is_starred,
                is_read=is_read,
            )
            paper_responses.append(paper_response)

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
    ) -> StarredPapersResponse:
        """Get starred papers for a user."""
        star_repo = UserStarRepository(db_session)
        starred_papers = star_repo.get_starred_papers(user_id, skip=skip, limit=limit)

        paper_responses = []
        for starred_paper in starred_papers:
            # Since these are starred papers, they are starred by the user
            is_starred = True

            # Check if user has read the summary
            is_read = False
            if starred_paper.paper_id is not None:
                summary_repo = SummaryRepository(db_session)
                summary = summary_repo.get_by_paper_id_and_language(
                    starred_paper.paper_id, "English"
                )
                if summary and summary.summary_id:
                    summary_read_repo = SummaryReadRepository(db_session)
                    is_read = summary_read_repo.is_summary_read_by_user(
                        user_id, summary.summary_id
                    )

            paper_response = PaperResponse.from_crawler_paper(
                starred_paper, None, is_starred=is_starred, is_read=is_read
            )
            paper_responses.append(paper_response)

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

    def _check_valid_user_and_paper(
        self,
        session: Session,
        user_id: int,
        paper_id: int,
    ) -> str:
        """Check if user and paper exist."""
        if not UserRepository(session).get_by_id(user_id):
            return f"User {user_id} not found"
        if not PaperRepository(session).get_by_id(paper_id):
            return f"Paper {paper_id} not found"
        return ""

    def add_star(
        self,
        session: Session,
        user_id: int | None,
        paper_id: int | None,
        note: str | None = None,
    ) -> StarResponse:
        """Add a star to a paper.

        Args:
            paper_id: Paper ID
            star_repo: User star repository
            current_user: Current user information
            note: Optional note for the star

        Returns:
            Star response
        """
        if user_id is None or paper_id is None:
            return StarResponse.failure_response("User or paper ID is None")
        if msg := self._check_valid_user_and_paper(session, user_id, paper_id):
            raise ValueError(msg)

        star_repo = UserStarRepository(session)
        if star_repo.is_paper_starred(user_id, paper_id):
            return StarResponse.failure_response(f"Paper {paper_id} is already starred")

        star_repo.add_user_star(user_id, paper_id, note)
        return StarResponse(
            success=True,
            is_starred=True,
            message="Paper starred successfully",
            paper_id=paper_id,
            note=note,
        )

    def remove_star(
        self,
        session: Session,
        user_id: int | None,
        paper_id: int | None,
    ) -> StarResponse:
        """Remove a star from a paper.

        Args:
            paper_id: Paper ID
            star_repo: User star repository
            current_user: Current user information

        Returns:
            Star response
        """
        if user_id is None or paper_id is None:
            return StarResponse.failure_response("User or paper ID is None")
        if msg := self._check_valid_user_and_paper(session, user_id, paper_id):
            raise ValueError(msg)

        star_repo = UserStarRepository(session)
        if star_repo.remove_user_star(user_id, paper_id):
            return StarResponse(
                success=True,
                message="Paper unstarred successfully",
                is_starred=False,
                paper_id=paper_id,
                note=None,
            )

        return StarResponse.failure_response(f"Paper {paper_id} is not starred")

    def is_paper_starred(
        self,
        session: Session,
        user_id: int | None,
        paper_id: int | None,
    ) -> StarResponse:
        """Check if a paper is starred by the user.

        Args:
            session: Database session
            user_id: User ID
            paper_id: Paper ID

        Returns:
            Star response with is_starred status
        """
        if user_id is None or paper_id is None:
            return StarResponse.failure_response("User or paper ID is None")
        if msg := self._check_valid_user_and_paper(session, user_id, paper_id):
            raise ValueError(msg)

        star_repo = UserStarRepository(session)
        if star_repo.is_paper_starred(user_id, paper_id):
            star = star_repo.get_user_star(user_id, paper_id)
            return StarResponse(
                success=True,
                is_starred=True,
                message=f"Paper {paper_id} is starred",
                paper_id=paper_id,
                note=star.note if star else None,
            )
        else:
            return StarResponse(
                success=True,
                is_starred=False,
                message=f"Paper {paper_id} is not starred",
                paper_id=paper_id,
                note=None,
            )
