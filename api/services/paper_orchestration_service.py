"""Paper orchestration service for coordinating paper creation and summarization."""

import json
from typing import AsyncGenerator

from api.services.paper_creation_service import PaperCreationService
from api.services.paper_summarization_service import PaperSummarizationService
from core import get_logger
from core.database.llm_sqlite_manager import LLMSQLiteManager
from core.database.repository import SummaryRepository
from core.database.sqlite_manager import SQLiteManager
from core.models import PaperCreateRequest as PaperCreate
from core.models import PaperResponse
from core.models.api.streaming import (
    StreamingCompleteEvent,
    StreamingErrorEvent,
    StreamingStatusEvent,
)
from core.models.database.entities import PaperEntity
from crawler.arxiv.client import ArxivClient
from crawler.summarizer.client import SummaryClient

logger = get_logger(__name__)


class PaperOrchestrationService:
    """Service for orchestrating paper creation and summarization."""

    def __init__(self) -> None:
        """Initialize paper orchestration service."""
        self.creation_service = PaperCreationService()
        self.summarization_service = PaperSummarizationService()

    async def create_paper_normal(
        self,
        paper_data: PaperCreate,
        db_manager: SQLiteManager,
        llm_db_manager: LLMSQLiteManager,
        arxiv_client: ArxivClient,
        summary_client: SummaryClient,
    ) -> PaperResponse:
        """Create paper with background summarization."""
        paper = await self.creation_service.create_paper(
            paper_data, db_manager, arxiv_client
        )
        self.summarization_service.start_background_summarization(
            paper,
            db_manager,
            llm_db_manager,
            summary_client,
            language=paper_data.summary_language,
        )
        return PaperResponse.from_crawler_paper(paper, None)

    async def create_paper_streaming(
        self,
        paper_data: PaperCreate,
        db_manager: SQLiteManager,
        arxiv_client: ArxivClient,
    ) -> PaperResponse:
        """Create paper without background summarization (for streaming)."""
        paper = await self.creation_service.create_paper(
            paper_data, db_manager, arxiv_client
        )
        return PaperResponse.from_crawler_paper(paper, None)

    async def get_paper(
        self, paper_identifier: str, db_manager: SQLiteManager
    ) -> PaperResponse:
        """Get a paper by ID or arXiv ID."""
        paper = self.creation_service.get_paper_by_identifier(
            paper_identifier, db_manager
        )
        if not paper:
            raise ValueError(f"Paper not found: {paper_identifier}")

        return PaperResponse.from_crawler_paper(paper, None)

    async def summarize_paper(
        self,
        paper_identifier: str,
        db_manager: SQLiteManager,
        llm_db_manager: LLMSQLiteManager,
        summary_client: SummaryClient,
        force_resummarize: bool = False,
        language: str = "Korean",
    ) -> None:
        """Summarize a paper synchronously."""
        paper = self.creation_service.get_paper_by_identifier(
            paper_identifier, db_manager
        )
        if not paper:
            raise ValueError(f"Paper not found: {paper_identifier}")

        await self.summarization_service.summarize_paper(
            paper,
            db_manager,
            llm_db_manager,
            summary_client,
            force_resummarize,
            language,
        )

    async def stream_paper_creation(
        self,
        paper_data: PaperCreate,
        db_manager: SQLiteManager,
        llm_db_manager: LLMSQLiteManager,
        arxiv_client: ArxivClient,
        summary_client: SummaryClient,
    ) -> AsyncGenerator[str, None]:
        """Stream paper creation and immediate summarization process.

        Streaming mode always performs immediate summarization (no background tasks).
        """
        try:
            yield self._create_event(StreamingStatusEvent(message="Creating paper..."))
            logger.info(f"Creating paper: {paper_data.url}")

            paper_response = await self.create_paper_streaming(
                paper_data, db_manager, arxiv_client
            )
            yield self._create_event(StreamingCompleteEvent(paper=paper_response))
            logger.info(f"Paper created successfully: {paper_response.arxiv_id}")

            logger.debug(f"Getting paper by identifier: {paper_response.arxiv_id}")
            logger.debug(f"DB manager type: {type(db_manager)}")
            logger.debug(
                f"DB manager connection: "
                f"{getattr(db_manager, 'connection', 'No connection attr')}"
            )

            paper = self.creation_service.get_paper_by_identifier(
                paper_response.arxiv_id, db_manager
            )
            if not paper:
                yield self._create_event(
                    StreamingErrorEvent(message="Paper not found after creation")
                )
                logger.error(f"Paper is not created: {paper_response.arxiv_id}")
                return

            logger.debug(f"Starting immediate summarization for paper {paper.arxiv_id}")
            logger.debug(
                f"LLM db_manager type before summarization: {type(llm_db_manager)}"
            )
            logger.debug(
                f"LLM db_manager connection before summarization: "
                f"{getattr(llm_db_manager, 'connection', 'No connection attr')}"
            )

            async for event in self._stream_immediate_summarization(
                paper,
                paper_response,
                db_manager,
                llm_db_manager,
                paper_data.summary_language,
                summary_client,
            ):
                yield event

        except Exception as e:
            yield self._create_event(StreamingErrorEvent(message=str(e)))
            logger.error(f"Summarization failed: {str(e)}")

    async def _stream_immediate_summarization(
        self,
        paper: PaperEntity,
        paper_response: PaperResponse,
        db_manager: SQLiteManager,
        llm_db_manager: LLMSQLiteManager,
        language: str,
        summary_client: SummaryClient,
    ) -> AsyncGenerator[str, None]:
        """Stream the immediate summarization process."""
        try:
            yield self._create_event(
                StreamingStatusEvent(message="Starting immediate summarization...")
            )
            logger.info(f"Starting summary: {paper.arxiv_id}")

            await self.summarization_service.summarize_paper(
                paper,
                db_manager,
                llm_db_manager,
                summary_client,
                force_resummarize=False,
                language=language,
            )

            # Get the updated paper with summary
            summary_repo = SummaryRepository(db_manager)
            summary = None
            if paper.paper_id is not None:
                summary = summary_repo.get_by_paper_and_language(
                    paper.paper_id, language
                )
            updated_paper = PaperResponse.from_crawler_paper(paper, summary)
            yield self._create_event(StreamingCompleteEvent(paper=updated_paper))
            logger.info(f"Summary completed: {paper.arxiv_id}")

        except Exception as e:
            yield self._create_event(
                StreamingErrorEvent(message=f"Summarization failed: {str(e)}")
            )
            yield self._create_event(StreamingCompleteEvent(paper=paper_response))
            logger.error(f"Summarization failed: {str(e)}")

    def _create_event(
        self, event: StreamingStatusEvent | StreamingCompleteEvent | StreamingErrorEvent
    ) -> str:
        """Create a streaming event string."""
        return f"data: {json.dumps(event.model_dump())}\n\n"
