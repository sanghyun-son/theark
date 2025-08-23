"""Streaming service for real-time paper processing updates."""

import asyncio
import json
from typing import AsyncGenerator

from api.services.paper_service import PaperService
from core.models import (
    PaperCreateRequest,
    PaperEntity,
    PaperResponse,
    StreamingCompleteEvent,
    StreamingErrorEvent,
    StreamingStatusEvent,
)


class StreamingService:
    """Service for handling streaming paper processing."""

    def __init__(self, paper_service: PaperService) -> None:
        """Initialize streaming service."""
        self.paper_service = paper_service

    async def stream_paper_creation(
        self, paper_data: PaperCreateRequest
    ) -> AsyncGenerator[str, None]:
        """Stream paper creation and summarization process."""
        try:
            yield self._create_event(StreamingStatusEvent(message="Creating paper..."))

            # Skip auto-summarization since we'll handle it explicitly in streaming
            paper_response = await self.paper_service.create_paper(
                paper_data, skip_auto_summarization=True
            )
            yield self._create_event(
                StreamingStatusEvent(message="Paper created successfully")
            )
            yield self._create_event(StreamingCompleteEvent(paper=paper_response))

            paper = self.paper_service._get_paper_by_identifier(paper_response.arxiv_id)
            if not paper:
                yield self._create_event(
                    StreamingErrorEvent(message="Paper not found after creation")
                )
                return

            if paper_data.summarize_now:
                async for event in self._stream_summarization(
                    paper, paper_data, paper_response
                ):
                    yield event

        except Exception as e:
            yield self._create_event(StreamingErrorEvent(message=str(e)))

    async def _stream_summarization(
        self,
        paper: PaperEntity,
        paper_data: PaperCreateRequest,
        paper_response: PaperResponse,
    ) -> AsyncGenerator[str, None]:
        """Stream the summarization process."""
        try:
            yield self._create_event(
                StreamingStatusEvent(message="Starting summarization...")
            )

            summary_task = asyncio.create_task(
                self.paper_service._summarize_paper_async(
                    paper,
                    paper_data.force_resummarize,
                    paper_data.summary_language,
                )
            )

            async for event in self._monitor_summarization_progress(summary_task):
                yield event

            async for event in self._handle_summarization_completion(
                summary_task, paper, paper_response
            ):
                yield event

        except Exception as e:
            yield self._create_event(
                StreamingErrorEvent(message=f"Summarization failed: {str(e)}")
            )
            yield self._create_event(StreamingCompleteEvent(paper=paper_response))

    async def _monitor_summarization_progress(
        self, summary_task: asyncio.Task[None]
    ) -> AsyncGenerator[str, None]:
        """Monitor summarization task progress."""
        while not summary_task.done():
            yield self._create_event(
                StreamingStatusEvent(message="Generating summary...")
            )
            await asyncio.sleep(3)

    async def _handle_summarization_completion(
        self,
        summary_task: asyncio.Task[None],
        paper: PaperEntity,
        paper_response: PaperResponse,
    ) -> AsyncGenerator[str, None]:
        """Handle summarization task completion."""
        try:
            await summary_task
            yield self._create_event(StreamingStatusEvent(message="Summary completed!"))

            updated_paper = await self.paper_service.get_paper(paper.arxiv_id)
            yield self._create_event(StreamingCompleteEvent(paper=updated_paper))

        except Exception as e:
            yield self._create_event(
                StreamingErrorEvent(message=f"Summarization failed: {str(e)}")
            )

    def _create_event(
        self, event: StreamingStatusEvent | StreamingCompleteEvent | StreamingErrorEvent
    ) -> str:
        """Create a streaming event string."""
        return f"data: {json.dumps(event.model_dump())}\n\n"
