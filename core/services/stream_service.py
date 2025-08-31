"""Stream service for handling streaming operations."""

import json
from collections.abc import AsyncGenerator
from typing import Any

from sqlmodel import Session

from core import get_logger
from core.database.repository.paper import PaperRepository
from core.llm.openai_client import UnifiedOpenAIClient
from core.models import PaperCreateRequest
from core.models.api.responses import PaperResponse
from core.services.paper_service import PaperService
from core.services.paper_summarization_service import PaperSummarizationService

logger = get_logger(__name__)


class StreamService:
    """Service for handling streaming operations."""

    def __init__(self, default_interests: list[str]) -> None:
        """Initialize stream service."""
        self.paper_service = PaperService()
        self.summarization_service = PaperSummarizationService(
            default_interests=default_interests
        )

    async def stream_paper_summarization(
        self,
        paper_data: PaperCreateRequest,
        db_session: Session,
        summary_client: UnifiedOpenAIClient,
    ) -> AsyncGenerator[str, None]:
        """Stream paper creation and summarization process.

        Args:
            paper_data: Paper data to create and summarize
            db_session: Database session
            summary_client: OpenAI client for summarization

        Yields:
            Server-Sent Events stream with progress updates
        """
        try:
            # Step 1: Create paper
            yield self._create_status_event("Creating paper...")

            paper_repo = PaperRepository(db_session)
            paper_response = await self.paper_service.create_paper(
                paper_data, paper_repo, summary_client
            )

            yield self._create_status_event(
                "Paper created successfully", paper_response
            )

            # Step 2: Get the actual paper object for summarization
            paper = self.paper_service._get_paper_by_identifier(
                paper_response.arxiv_id, db_session
            )

            if not paper:
                raise ValueError("Failed to retrieve created paper")

            # Step 3: Summarize the paper
            yield self._create_status_event("Starting summarization...")

            summary = await self.summarization_service.summarize_paper(
                paper,
                db_session,
                summary_client,
                language=paper_data.summary_language,
            )

            if summary:
                yield self._create_status_event("Summarization completed")
            else:
                yield self._create_status_event(
                    "Summarization skipped (already exists)"
                )

            # Step 4: Get final paper with summary
            final_paper = await self.paper_service.get_paper(
                paper_response.arxiv_id,
                db_session,
                language=paper_data.summary_language,
            )

            # Step 5: Send complete event with final paper data
            yield self._create_complete_event(final_paper)

        except Exception as e:
            yield self._create_error_event(str(e))

    def _create_status_event(
        self,
        message: str,
        paper_response: PaperResponse | None = None,
    ) -> str:
        """Create a status event."""
        event: dict[str, Any] = {"type": "status", "message": message}
        if paper_response:
            event["paper"] = paper_response.model_dump()
        return f"data: {json.dumps(event)}\n"

    def _create_complete_event(self, paper_response: PaperResponse) -> str:
        """Create a complete event with paper data."""
        event: dict[str, Any] = {
            "type": "complete",
            "paper": paper_response.model_dump(),
        }
        return f"data: {json.dumps(event)}\n"

    def _create_error_event(self, message: str) -> str:
        """Create an error event."""
        event: dict[str, Any] = {"type": "error", "message": message}
        return f"data: {json.dumps(event)}\n"
