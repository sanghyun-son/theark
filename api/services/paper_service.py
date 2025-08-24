"""Paper service for CRUD operations using new architecture."""

from typing import AsyncGenerator

from api.services.paper_creation_service import PaperCreationService
from api.services.paper_orchestration_service import PaperOrchestrationService
from api.services.paper_summarization_service import PaperSummarizationService
from core import get_logger
from core.config import load_settings
from core.models import PaperCreateRequest as PaperCreate
from core.models import (
    PaperDeleteResponse,
    PaperListResponse,
    PaperResponse,
    SummaryEntity,
    SummaryReadResponse,
)
from core.models.api.responses import StarredPapersResponse, StarResponse
from core.models.database.entities import PaperEntity, UserStarEntity
from core.models.domain.user import User
from crawler.arxiv.client import ArxivClient
from crawler.database import (
    PaperRepository,
    SummaryRepository,
    UserRepository,
)
from crawler.database.llm_sqlite_manager import LLMSQLiteManager
from crawler.database.sqlite_manager import SQLiteManager
from crawler.summarizer.client import SummaryClient
from crawler.summarizer.service import SummarizationService

logger = get_logger(__name__)


class PaperService:
    """Service for paper CRUD operations using new architecture."""

    def __init__(self) -> None:
        """Initialize paper service."""
        self.settings = load_settings()

    def _initialize_summarization_service(
        self, llm_db_manager: LLMSQLiteManager
    ) -> SummarizationService:
        """Initialize summarization service."""
        try:
            summarization_service = SummarizationService()
            return summarization_service
        except Exception as e:
            logger.error(
                f"Failed to initialize SummarizationService: {e}",
                exc_info=True,
            )
            raise

    async def create_paper(
        self,
        paper_data: PaperCreate,
        db_manager: SQLiteManager,
        llm_db_manager: LLMSQLiteManager,
        arxiv_client: ArxivClient,
        summary_client: SummaryClient,
        skip_auto_summarization: bool = False,
    ) -> PaperResponse:
        """Create a new paper using new architecture."""
        creation_service = PaperCreationService()
        summarization_service_wrapper = PaperSummarizationService()
        orchestration_service = PaperOrchestrationService(
            creation_service, summarization_service_wrapper
        )

        if skip_auto_summarization:
            return await orchestration_service.create_paper_streaming(
                paper_data, db_manager, arxiv_client
            )
        else:
            return await orchestration_service.create_paper_normal(
                paper_data, db_manager, llm_db_manager, arxiv_client, summary_client
            )

    async def get_paper(
        self,
        paper_identifier: str,
        db_manager: SQLiteManager,
        llm_db_manager: LLMSQLiteManager,
    ) -> PaperResponse:
        """Get a paper by ID or arXiv ID."""
        creation_service = PaperCreationService()
        summarization_service_wrapper = PaperSummarizationService()
        orchestration_service = PaperOrchestrationService(
            creation_service, summarization_service_wrapper
        )
        return await orchestration_service.get_paper(paper_identifier, db_manager)

    async def create_paper_streaming(
        self,
        paper_data: PaperCreate,
        db_manager: SQLiteManager,
        llm_db_manager: LLMSQLiteManager,
        arxiv_client: ArxivClient,
        summary_client: SummaryClient,
    ) -> AsyncGenerator[str, None]:
        """Create a paper with streaming response."""
        creation_service = PaperCreationService()
        summarization_service_wrapper = PaperSummarizationService()
        orchestration_service = PaperOrchestrationService(
            creation_service, summarization_service_wrapper
        )

        async for event in orchestration_service.stream_paper_creation(
            paper_data, db_manager, llm_db_manager, arxiv_client, summary_client
        ):
            yield event

    async def delete_paper(
        self, paper_identifier: str, db_manager: SQLiteManager
    ) -> PaperDeleteResponse:
        """Delete a paper by ID or arXiv ID."""
        paper_repo = PaperRepository(db_manager)
        paper = self._get_paper_by_identifier(paper_identifier, paper_repo)
        if not paper:
            raise ValueError("Paper not found")

        # Delete paper (this will cascade to summaries due to foreign key constraints)
        if paper.paper_id is not None:
            paper_repo.delete(paper.paper_id)
        else:
            raise ValueError("Paper has no ID")

        return PaperDeleteResponse(
            success=True,
            message=f"Paper {paper_identifier} deleted successfully",
        )

    async def get_papers(
        self,
        db_manager: SQLiteManager,
        limit: int = 20,
        offset: int = 0,
        language: str = "Korean",
    ) -> PaperListResponse:
        """Get papers with pagination."""
        paper_repo = PaperRepository(db_manager)
        summary_repo = SummaryRepository(db_manager)

        try:
            papers, total_count = paper_repo.get_papers_paginated(limit, offset)
            paper_responses = []

            for paper in papers:
                summary = self._get_paper_summary(paper, summary_repo, language)
                paper_response = PaperResponse.from_crawler_paper(paper, summary)
                paper_responses.append(paper_response)

            has_more = total_count > (offset + limit)

            return PaperListResponse(
                papers=paper_responses,
                total_count=total_count,
                limit=limit,
                offset=offset,
                has_more=has_more,
            )

        except Exception as e:
            logger.error(f"Error getting papers: {e}")
            raise ValueError(f"Failed to get papers: {e}")

    async def mark_summary_as_read(
        self, paper_id: int, summary_id: int, db_manager: SQLiteManager
    ) -> SummaryReadResponse:
        """Mark a summary as read."""
        summary_repo = SummaryRepository(db_manager)
        summary = summary_repo.get_by_id(summary_id)
        if not summary:
            raise ValueError(f"Summary {summary_id} not found")

        if summary.paper_id != paper_id:
            raise ValueError(
                f"Summary {summary_id} does not belong to paper {paper_id}"
            )

        # Update the summary to mark it as read
        summary.is_read = True
        summary_repo.update(summary)

        return SummaryReadResponse(
            success=True,
            message=f"Summary {summary_id} marked as read",
            summary_id=summary_id,
            is_read=True,
        )

    # Star functionality methods
    async def add_star(
        self,
        paper_id: int,
        db_manager: SQLiteManager,
        user: User,
        note: str | None = None,
    ) -> StarResponse:
        """Add a star to a paper."""
        if user.user_id is None:
            raise ValueError("User ID is required")

        paper_repo = PaperRepository(db_manager)
        paper = paper_repo.get_by_id(paper_id)
        if not paper:
            raise ValueError(f"Paper {paper_id} not found")

        star = UserStarEntity(
            user_id=user.user_id,
            paper_id=paper_id,
            note=note,
        )

        # Add star to database
        user_repo = UserRepository(db_manager)
        user_repo.add_star(star)

        return StarResponse(
            success=True,
            message=f"Paper {paper_id} starred successfully",
            paper_id=paper_id,
            is_starred=True,
            note=note,
            created_at=star.created_at,
        )

    async def remove_star(
        self, paper_id: int, db_manager: SQLiteManager, user: User
    ) -> StarResponse:
        """Remove a star from a paper."""
        if user.user_id is None:
            raise ValueError("User ID is required")

        paper_repo = PaperRepository(db_manager)
        paper = paper_repo.get_by_id(paper_id)
        if not paper:
            raise ValueError(f"Paper {paper_id} not found")

        user_repo = UserRepository(db_manager)
        user_repo.remove_star(user.user_id, paper_id)

        return StarResponse(
            success=True,
            message=f"Star removed from paper {paper_id}",
            paper_id=paper_id,
            is_starred=False,
            note=None,
            created_at=None,
        )

    async def get_starred_papers(
        self,
        db_manager: SQLiteManager,
        user: User,
        limit: int = 20,
        offset: int = 0,
    ) -> StarredPapersResponse:
        """Get all starred papers for the current user."""
        if user.user_id is None:
            raise ValueError("User ID is required")

        paper_repo = PaperRepository(db_manager)
        summary_repo = SummaryRepository(db_manager)

        user_repo = UserRepository(db_manager)
        stars = user_repo.get_user_stars(user.user_id, limit=limit + offset)

        # Apply offset
        stars = stars[offset : offset + limit]

        # Get paper details for each star
        papers = []
        for star in stars:
            paper = paper_repo.get_by_id(star.paper_id)
            if paper:
                # Get summary if available
                summary = None
                summaries = summary_repo.get_by_paper_id(star.paper_id)
                if summaries:
                    summary = summaries[0]  # Get the first summary

                # Create PaperResponse
                from core.models.api.responses import PaperResponse

                paper_response = PaperResponse.from_crawler_paper(paper, summary)
                papers.append(paper_response)

        return StarredPapersResponse(
            papers=papers,
            total_count=len(
                papers
            ),  # This should be the total count, not just current page
            limit=limit,
            offset=offset,
        )

    async def is_paper_starred(
        self, paper_id: int, db_manager: SQLiteManager, user: User
    ) -> StarResponse:
        """Check if a paper is starred by the current user."""
        if user.user_id is None:
            raise ValueError("User ID is required")

        user_repo = UserRepository(db_manager)
        paper_repo = PaperRepository(db_manager)

        paper = paper_repo.get_by_id(paper_id)
        if not paper:
            raise ValueError(f"Paper {paper_id} not found")

        stars = user_repo.get_user_stars(user.user_id, limit=1000)  # Get all stars
        starred_paper = next(
            (star for star in stars if star.paper_id == paper_id), None
        )

        if starred_paper:
            return StarResponse(
                success=True,
                message=f"Paper {paper_id} is starred",
                paper_id=paper_id,
                is_starred=True,
                note=starred_paper.note,
                created_at=starred_paper.created_at,
            )
        else:
            return StarResponse(
                success=True,
                message=f"Paper {paper_id} is not starred",
                paper_id=paper_id,
                is_starred=False,
                note=None,
                created_at=None,
            )

    def _get_paper_by_identifier(
        self, paper_identifier: str, paper_repo: PaperRepository
    ) -> PaperEntity | None:
        """Get paper by ID or arXiv ID."""
        # Try to get by arXiv ID first
        paper = paper_repo.get_by_arxiv_id(paper_identifier)
        if paper:
            return paper

        # Try to get by paper ID
        try:
            paper_id = int(paper_identifier)
            return paper_repo.get_by_id(paper_id)
        except ValueError:
            return None

    def _get_paper_summary(
        self,
        paper: PaperEntity,
        summary_repo: SummaryRepository,
        language: str = "Korean",
    ) -> SummaryEntity | None:
        """Get summary for a paper in specified language (legacy method)."""
        if not paper.paper_id:
            return None

        try:
            summary_obj = summary_repo.get_by_paper_and_language(
                paper.paper_id, language
            )
            if not summary_obj and language != "English":
                summary_obj = summary_repo.get_by_paper_and_language(
                    paper.paper_id, "English"
                )

            return summary_obj
        except Exception as e:
            logger.error(f"Error getting paper summary for {paper.arxiv_id}: {e}")
            return None

    async def get_summary(
        self, paper_id: int, summary_id: int, db_manager: SQLiteManager
    ) -> SummaryEntity:
        """Get a specific summary by ID."""
        summary_repo = SummaryRepository(db_manager)
        summary = summary_repo.get_by_id(summary_id)
        if not summary:
            raise ValueError(f"Summary {summary_id} not found")

        # Verify the summary belongs to the correct paper
        if summary.paper_id != paper_id:
            raise ValueError(
                f"Summary {summary_id} does not belong to paper {paper_id}"
            )

        return summary

    async def stream_paper_creation(
        self,
        paper_data: PaperCreate,
        db_manager: SQLiteManager,
        llm_db_manager: LLMSQLiteManager,
        arxiv_client: ArxivClient,
        summary_client: SummaryClient,
    ) -> AsyncGenerator[str, None]:
        """Stream paper creation and summarization process."""
        creation_service = PaperCreationService()
        summarization_service_wrapper = PaperSummarizationService()
        orchestration_service = PaperOrchestrationService(
            creation_service, summarization_service_wrapper
        )

        async for event in orchestration_service.stream_paper_creation(
            paper_data, db_manager, llm_db_manager, arxiv_client, summary_client
        ):
            yield event

    async def close(self) -> None:
        """Close the service and cleanup resources."""
        # Cleanup resources if needed
        pass
