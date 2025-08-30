"""Paper orchestration service for coordinating paper creation and summarization."""

import json
from collections.abc import AsyncGenerator

from sqlmodel import Session

from core import get_logger
from core.database.repository import SummaryRepository
from core.database.repository.paper import PaperRepository
from core.llm.openai_client import UnifiedOpenAIClient
from core.models import PaperCreateRequest
from core.models.api.responses import PaperResponse
from core.models.api.streaming import (
    StreamingCompleteEvent,
    StreamingErrorEvent,
    StreamingStatusEvent,
)
from core.models.rows import Paper
from core.services.paper_creation_service import PaperCreationService
from core.services.paper_summarization_service import PaperSummarizationService

logger = get_logger(__name__)


class PaperOrchestrationService:
    """Service for orchestrating paper creation and summarization."""

    def __init__(
        self,
        default_interests: list[str] = ["Machine Learning"],
    ) -> None:
        """Initialize paper orchestration service."""

        self.creation_service = PaperCreationService()
        self.summarization_service = PaperSummarizationService(
            version="0.1.0",
            default_interests=default_interests,
        )

    async def create_paper_normal(
        self,
        paper_data: PaperCreateRequest,
        paper_repo: PaperRepository,
        llm_client: UnifiedOpenAIClient,
    ) -> Paper:
        """Create paper with background summarization."""
        paper = await self.creation_service.create_paper(paper_data, paper_repo)

        # Only start background summarization if not skipped
        if not paper_data.skip_auto_summarization:
            await self.summarization_service.summarize_paper(
                paper,
                paper_repo.db,
                llm_client,
                language=paper_data.summary_language,
            )

        return paper

    async def create_paper_streaming(
        self,
        paper_data: PaperCreateRequest,
        paper_repo: PaperRepository,
    ) -> Paper:
        """Create paper without background summarization (for streaming)."""
        paper = await self.creation_service.create_paper(paper_data, paper_repo)
        return paper

    async def get_paper(self, paper_identifier: str, db_session: Session) -> Paper:
        """Get a paper by ID or arXiv ID."""
        paper = await self.creation_service.get_paper_by_identifier(
            paper_identifier, db_session
        )
        if not paper:
            raise ValueError(f"Paper not found: {paper_identifier}")

        return paper

    async def summarize_paper(
        self,
        paper_identifier: str,
        db_session: Session,
        llm_client: UnifiedOpenAIClient,
        force_resummarize: bool = False,
        language: str = "Korean",
    ) -> None:
        """Summarize a paper synchronously."""
        paper = await self.creation_service.get_paper_by_identifier(
            paper_identifier, db_session
        )
        if not paper:
            raise ValueError(f"Paper not found: {paper_identifier}")

        await self.summarization_service.summarize_paper(
            paper,
            db_session,
            llm_client,
            force_resummarize,
            language,
        )

    async def summarize_stream(
        self,
        paper_data: PaperCreateRequest,
        db_session: Session,
        llm_client: UnifiedOpenAIClient,
    ) -> AsyncGenerator[str, None]:
        """Stream paper creation and immediate summarization process.

        Streaming mode always performs immediate summarization (no background tasks).
        """
        try:
            yield self._create_event(StreamingStatusEvent(message="Creating paper..."))
            logger.info(f"[{paper_data.url}] Creating")

            paper_repo = PaperRepository(db_session)
            created = await self.creation_service.create_paper(paper_data, paper_repo)

            paper = paper_repo.get_by_arxiv_id(created.arxiv_id)
            if paper is None:
                yield self._create_event(
                    StreamingErrorEvent(message="Paper not found after creation")
                )
                logger.error(f"[{created.arxiv_id}] Not created")
                return
            else:
                paper_response_obj = PaperResponse.from_crawler_paper(paper)
                yield self._create_event(
                    StreamingCompleteEvent(paper=paper_response_obj)
                )
                logger.info(f"[{paper.arxiv_id}] Successfully created")

            # Stream immediate summarization using the same session
            async for event in self._stream_immediate_summarization(
                paper,
                created,
                db_session,
                paper_data.summary_language,
                llm_client,
            ):
                yield event

        except Exception as e:
            yield self._create_event(StreamingErrorEvent(message=str(e)))
            logger.error(f"Summarization failed: {str(e)}")

    async def _stream_immediate_summarization(
        self,
        paper: Paper,
        paper_response: Paper,
        db_session: Session,
        language: str,
        llm_client: UnifiedOpenAIClient,
    ) -> AsyncGenerator[str, None]:
        """Stream the immediate summarization process."""
        try:
            yield self._create_event(
                StreamingStatusEvent(message="Starting immediate summarization...")
            )
            logger.info(f"[{paper.arxiv_id}] Starting summary")

            # Use the existing session for summarization
            await self.summarization_service.summarize_paper(
                paper,
                db_session,
                llm_client,
                force_resummarize=False,
                language=language,
            )

            # Get the updated paper with summary
            summary_repo = SummaryRepository(db_session)
            summary = None
            if paper.paper_id is not None:
                summary = summary_repo.get_by_paper_id_and_language(
                    paper.paper_id, language
                )
            updated_paper = paper
            paper_response_obj = PaperResponse.from_crawler_paper(
                updated_paper, summary=summary
            )
            yield self._create_event(StreamingCompleteEvent(paper=paper_response_obj))
            logger.info(f"[{paper.arxiv_id}] Summary completed")

        except Exception as e:
            yield self._create_event(
                StreamingErrorEvent(message=f"Summarization failed: {str(e)}")
            )
            paper_response_obj = PaperResponse.from_crawler_paper(paper_response)
            yield self._create_event(StreamingCompleteEvent(paper=paper_response_obj))
            logger.error(f"[{paper.arxiv_id}] Summarization failed: {str(e)}")

    def _create_event(
        self, event: StreamingStatusEvent | StreamingCompleteEvent | StreamingErrorEvent
    ) -> str:
        """Create a streaming event string."""
        return f"data: {json.dumps(event.model_dump())}\n"
