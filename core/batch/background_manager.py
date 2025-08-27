"""Background batch processing manager."""

import asyncio
import json
import tempfile
from pathlib import Path
from typing import Any

from core.batch.state_manager import BatchStateManager
from core.config import Settings
from core.database.interfaces import DatabaseManager
from core.llm.batch_builder import UnifiedBatchBuilder
from core.llm.openai_client import UnifiedOpenAIClient
from core.log import get_logger
from core.models.batch import (
    BatchItem,
    BatchMetadata,
    BatchRequestPayload,
    BatchResult,
    PaperSummary,
)

logger = get_logger(__name__)


class BackgroundBatchManager:
    """Manages background batch processing tasks."""

    def __init__(self, settings: Settings) -> None:
        """Initialize background batch manager.

        Args:
            settings: Application settings
        """
        self._settings = settings
        self._state_manager = BatchStateManager()
        self._running = False
        self._summary_task: asyncio.Task[Any] | None = None
        self._fetch_task: asyncio.Task[Any] | None = None

    async def start(
        self,
        db_manager: DatabaseManager,
        openai_client: UnifiedOpenAIClient,
    ) -> None:
        """Start background batch processing.

        Args:
            db_manager: Database manager instance
            openai_client: OpenAI batch client instance
        """
        if self._running:
            logger.warning("Background batch manager is already running")
            return

        if not self._settings.batch_enabled:
            logger.info("Batch processing is disabled in settings")
            return

        logger.info("Starting background batch manager")
        self._running = True

        # Start summary scheduler (runs every hour)
        self._summary_task = asyncio.create_task(
            self._summary_scheduler(db_manager, openai_client)
        )

        # Start fetch scheduler (runs every 10 minutes)
        self._fetch_task = asyncio.create_task(
            self._fetch_scheduler(db_manager, openai_client)
        )

        logger.info("Background batch manager started successfully")

    async def stop(self) -> None:
        """Stop background batch processing."""
        if not self._running:
            logger.warning("Background batch manager is not running")
            return

        logger.info("Stopping background batch manager")
        self._running = False

        async def _cancel_task(
            task: asyncio.Task[Any] | None,
        ) -> asyncio.Task[Any] | None:
            """Cancel a task and wait for it to complete."""
            if task is None:
                return None
            task.cancel()
            try:
                await task
            except asyncio.CancelledError:
                pass
            return None

        self._summary_task = await _cancel_task(self._summary_task)
        self._fetch_task = await _cancel_task(self._fetch_task)
        logger.info("Background batch manager stopped successfully")

    async def _summary_scheduler(
        self, db_manager: DatabaseManager, openai_client: UnifiedOpenAIClient
    ) -> None:
        """Scheduler for creating batch requests for pending summaries.

        Args:
            db_manager: Database manager instance
            openai_client: OpenAI batch client instance
        """
        logger.info("Summary scheduler started")

        while self._running:
            try:
                await self._process_pending_summaries(db_manager, openai_client)
                await asyncio.sleep(self._settings.batch_summary_interval)
            except asyncio.CancelledError:
                logger.info("Summary scheduler cancelled")
                break
            except Exception as e:
                logger.error(f"Error in summary scheduler: {e}")
                await asyncio.sleep(60)  # Wait 1 minute before retrying

    async def _fetch_scheduler(
        self, db_manager: DatabaseManager, openai_client: UnifiedOpenAIClient
    ) -> None:
        """Scheduler for fetching batch results.

        Args:
            db_manager: Database manager instance
            openai_client: OpenAI batch client instance
        """
        logger.info("Fetch scheduler started")

        while self._running:
            try:
                await self._process_active_batches(db_manager, openai_client)
                await asyncio.sleep(self._settings.batch_fetch_interval)
            except asyncio.CancelledError:
                logger.info("Fetch scheduler cancelled")
                break
            except Exception as e:
                logger.error(f"Error in fetch scheduler: {e}")
                await asyncio.sleep(60)  # Wait 1 minute before retrying

    async def _process_pending_summaries(
        self, db_manager: DatabaseManager, openai_client: UnifiedOpenAIClient
    ) -> None:
        """Process pending summaries and create batch requests.

        Args:
            db_manager: Database manager instance
            openai_client: OpenAI batch client instance
        """
        try:
            # Get pending summaries
            pending_papers = await self._state_manager.get_pending_summaries(db_manager)

            if not pending_papers:
                logger.debug("No pending summaries to process")
                return

            # Check daily limit
            if not await self._check_daily_limit(db_manager):
                logger.warning("Daily batch limit reached, skipping summary processing")
                return

            logger.info(f"Processing {len(pending_papers)} pending summaries")

            # Convert dicts to PaperSummary objects
            paper_summaries = [
                PaperSummary(
                    paper_id=paper["paper_id"],
                    title=paper["title"],
                    abstract=paper["abstract"],
                    arxiv_id=paper["arxiv_id"],
                    published_at=paper.get("published_at"),
                )
                for paper in pending_papers
            ]

            # Mark papers as processing to prevent race conditions
            paper_ids = [paper["paper_id"] for paper in pending_papers]
            await self._state_manager.mark_papers_processing(paper_ids)

            # Create batch request
            await self._create_batch_request(db_manager, paper_summaries, openai_client)

        except Exception as e:
            logger.error(f"Error processing pending summaries: {e}")

    async def _create_batch_request(
        self,
        db_manager: DatabaseManager,
        papers: list[PaperSummary],
        openai_client: UnifiedOpenAIClient,
    ) -> None:
        """Create a batch request for paper summarization.

        Args:
            db_manager: Database manager instance
            papers: List of papers to summarize
        """
        try:
            # Limit papers to batch_max_items
            papers = papers[: self._settings.batch_max_items]

            # Create batch request payload
            batch_payload = self._create_batch_payload(papers, openai_client)

            # Upload data to OpenAI
            file_id = await openai_client.upload_data(
                batch_payload.to_jsonl(), "batch_requests.jsonl", purpose="batch"
            )

            # Create batch request
            batch_metadata = BatchMetadata(
                purpose="paper_summarization",
                paper_count=len(papers),
                model=openai_client.model,  # Use the model from the client
            )
            batch_response = await openai_client.create_batch_request(
                input_file_id=file_id,
                completion_window="24h",
                endpoint="/v1/chat/completions",
                metadata=batch_metadata.model_dump(),
            )

            # Store batch record in database
            if not batch_response.id:
                raise RuntimeError("Batch response missing ID")

            await self._state_manager.create_batch_record(
                db_manager,
                batch_id=batch_response.id,
                input_file_id=file_id,
                completion_window="24h",
                endpoint="/v1/chat/completions",
                metadata=batch_metadata.model_dump(),
            )

            # Add batch items to database
            batch_items = []
            for paper in papers:
                batch_item = BatchItem(
                    paper_id=paper.paper_id,
                    input_data=json.dumps(
                        {
                            "paper_id": paper.paper_id,
                            "title": paper.title,
                            "abstract": paper.abstract,
                            "arxiv_id": paper.arxiv_id,
                        }
                    ),
                )
                batch_items.append(batch_item.model_dump())

            await self._state_manager.add_batch_items(
                db_manager, batch_response.id, batch_items
            )

            logger.info(
                f"Created batch request {batch_response.id} for {len(papers)} papers"
            )

        except Exception as e:
            logger.error(f"Error creating batch request: {e}")
            raise

    def _create_batch_payload(
        self, papers: list[PaperSummary], openai_client: UnifiedOpenAIClient
    ) -> BatchRequestPayload:
        """Create batch request payload using unified prompt structure.

        Args:
            papers: List of papers to include in batch

        Returns:
            Batch request payload
        """
        papers_data = [
            {
                "paper_id": paper.paper_id,
                "title": paper.title,
                "abstract": paper.abstract,
                "arxiv_id": paper.arxiv_id,
            }
            for paper in papers
        ]

        return UnifiedBatchBuilder.create_paper_summarization_batch(
            papers_data,
            interest_section="",  # TODO: Get from config or user preferences
            language="English",
            model=openai_client.model,  # Use the model from the client
            use_tools=True,  # Batch API supports tool calling
        )

    async def _process_active_batches(
        self, db_manager: DatabaseManager, openai_client: UnifiedOpenAIClient
    ) -> None:
        """Process active batch requests and fetch results.

        Args:
            db_manager: Database manager instance
        """
        try:
            # Get active batches
            active_batches = await self._state_manager.get_active_batches(db_manager)

            if not active_batches:
                logger.debug("No active batches to process")
                return

            logger.info(f"Processing {len(active_batches)} active batches")

            # Process each active batch
            for batch in active_batches:
                await self._process_batch_status(db_manager, batch, openai_client)

        except Exception as e:
            logger.error(f"Error processing active batches: {e}")

    async def _process_batch_status(
        self,
        db_manager: DatabaseManager,
        batch: dict[str, Any],
        openai_client: UnifiedOpenAIClient,
    ) -> None:
        """Process status of a single batch.

        Args:
            db_manager: Database manager instance
            batch: Batch information from database
        """
        try:
            batch_id = batch["batch_id"]

            # Get current status from OpenAI
            batch_status = await openai_client.get_batch_status(batch_id)

            # Update batch status in database
            await self._state_manager.update_batch_status(
                db_manager,
                batch_id=batch_id,
                status=batch_status.status,
                output_file_id=batch_status.output_file_id,
                error_file_id=batch_status.error_file_id,
                request_counts=batch_status.request_counts,
            )

            # If batch is completed, process results
            if batch_status.status == "completed" and batch_status.output_file_id:
                await self._process_batch_results(
                    db_manager, batch_id, batch_status.output_file_id, openai_client
                )

            # If batch failed, log error
            elif batch_status.status == "failed":
                logger.error(f"Batch {batch_id} failed")
                if batch_status.error_file_id:
                    await self._process_batch_errors(
                        db_manager, batch_id, batch_status.error_file_id, openai_client
                    )

            logger.debug(f"Updated batch {batch_id} status to {batch_status.status}")

        except Exception as e:
            logger.error(
                f"Error processing batch {batch.get('batch_id', 'unknown')}: {e}"
            )

    async def _process_batch_results(
        self,
        db_manager: DatabaseManager,
        batch_id: str,
        output_file_id: str,
        openai_client: UnifiedOpenAIClient,
    ) -> None:
        """Process completed batch results.

        Args:
            db_manager: Database manager instance
            batch_id: ID of the completed batch
            output_file_id: ID of the output file
        """
        try:
            # Download output file
            output_file_path = tempfile.mktemp(suffix=".jsonl")
            await openai_client.download_file(output_file_id, output_file_path)

            # Process each result
            with open(output_file_path, "r") as f:
                for line in f:
                    if line.strip():
                        result = json.loads(line)
                        await self._process_single_result(db_manager, batch_id, result)

            # Clean up
            Path(output_file_path).unlink(missing_ok=True)

            logger.info(f"Processed results for batch {batch_id}")

        except Exception as e:
            logger.error(f"Error processing batch results for {batch_id}: {e}")

    async def _process_single_result(
        self, db_manager: DatabaseManager, batch_id: str, result: BatchResult
    ) -> None:
        """Process a single batch result.

        Args:
            db_manager: Database manager instance
            batch_id: ID of the batch
            result: Single result from batch
        """
        try:
            custom_id = result.custom_id
            if not custom_id:
                logger.warning(f"No custom_id in batch result: {result}")
                return

            paper_id = int(custom_id)

            # Check if result was successful
            if result.status_code == 200:
                response_body = result.response.get("body", {})
                summary_text = (
                    response_body.get("choices", [{}])[0]
                    .get("message", {})
                    .get("content", "")
                )

                # Update batch item status
                await self._state_manager.update_batch_item_status(
                    db_manager,
                    batch_id=batch_id,
                    paper_id=paper_id,
                    status="completed",
                    output_data=summary_text,
                )

                logger.debug(f"Processed successful result for paper {paper_id}")
            else:
                # Handle failed result
                error_message = (
                    result.response.get("body", {})
                    .get("error", {})
                    .get("message", "Unknown error")
                )

                await self._state_manager.update_batch_item_status(
                    db_manager,
                    batch_id=batch_id,
                    paper_id=paper_id,
                    status="failed",
                    error_message=error_message,
                )

                logger.warning(f"Failed result for paper {paper_id}: {error_message}")

        except Exception as e:
            logger.error(f"Error processing single result for batch {batch_id}: {e}")

    async def _process_batch_errors(
        self,
        db_manager: DatabaseManager,
        batch_id: str,
        error_file_id: str,
        openai_client: UnifiedOpenAIClient,
    ) -> None:
        """Process batch error file.

        Args:
            db_manager: Database manager instance
            batch_id: ID of the batch
            error_file_id: ID of the error file
        """
        try:
            # Download error file
            error_file_path = tempfile.mktemp(suffix=".jsonl")
            await openai_client.download_file(error_file_id, error_file_path)

            # Log errors
            with open(error_file_path, "r") as f:
                for line in f:
                    if line.strip():
                        error = json.loads(line)
                        logger.error(f"Batch {batch_id} error: {error}")

            # Clean up
            Path(error_file_path).unlink(missing_ok=True)

        except Exception as e:
            logger.error(f"Error processing batch errors for {batch_id}: {e}")

    async def _check_daily_limit(self, db_manager: DatabaseManager) -> bool:
        """Check if daily batch limit has been reached.

        Args:
            db_manager: Database manager instance

        Returns:
            True if under daily limit, False otherwise
        """
        # TODO: Implement daily limit checking
        # For now, always return True
        return True

    @property
    def is_running(self) -> bool:
        """Check if background manager is running."""
        return self._running

    async def trigger_processing(
        self,
        db_manager: DatabaseManager,
        openai_client: UnifiedOpenAIClient,
    ) -> None:
        """Manually trigger batch processing.

        Args:
            db_manager: Database manager instance
            openai_client: OpenAI batch client instance
        """
        await self._process_pending_summaries(db_manager, openai_client)
