"""Background batch processing manager."""

import asyncio
import json
import tempfile
from pathlib import Path
from typing import Any

from sqlalchemy.engine import Engine

from core.batch.state_manager import BatchStateManager
from core.llm.batch_builder import UnifiedBatchBuilder
from core.llm.openai_client import UnifiedOpenAIClient
from core.log import get_logger
from core.models.batch import BatchRequestPayload, BatchResult
from core.models.rows import Paper
from core.services.summarization_service import PaperSummarizationService

logger = get_logger(__name__)


class BackgroundBatchManager:
    """Manages background batch processing tasks."""

    def __init__(
        self,
        summary_service: PaperSummarizationService,
        batch_summary_interval: int = 3600,
        batch_fetch_interval: int = 600,
        batch_max_items: int = 1000,
        batch_daily_limit: int = 10000,
        language: str = "English",
        interests: list[str] = ["Machine Learning"],
    ) -> None:
        """Initialize background batch manager.

        Args:
            summary_service: Paper summarization service instance
            batch_summary_interval: Interval in seconds for summary batch processing
            batch_fetch_interval: Interval in seconds for fetching batch results
            batch_max_items: Maximum number of items per batch
            batch_daily_limit: Maximum number of batch requests per day
            language: Language for batch summarization (default: "English")
        """
        self._batch_summary_interval = batch_summary_interval
        self._batch_fetch_interval = batch_fetch_interval
        self._batch_max_items = batch_max_items
        self._batch_daily_limit = batch_daily_limit
        self._language = language

        self._interests = interests

        self._state_manager = BatchStateManager()
        self._summary_service = summary_service
        self._running = False
        self._summary_task: asyncio.Task[Any] | None = None
        self._fetch_task: asyncio.Task[Any] | None = None

    async def start(
        self,
        db_engine: Engine,
        openai_client: UnifiedOpenAIClient,
    ) -> None:
        """Start background batch processing.

        Args:
            db_session: Database manager instance
            openai_client: OpenAI batch client instance
        """
        if self._running:
            logger.warning("Background batch manager is already running")
            return

        logger.info("Starting background batch manager")
        self._running = True

        # Start summary scheduler (runs every hour)
        self._summary_task = asyncio.create_task(
            self._summary_scheduler(db_engine, openai_client)
        )

        # Start fetch scheduler (runs every 10 minutes)
        self._fetch_task = asyncio.create_task(
            self._fetch_scheduler(db_engine, openai_client)
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
        self, db_engine: Engine, openai_client: UnifiedOpenAIClient
    ) -> None:
        """Scheduler for creating batch requests for pending summaries.

        Args:
            db_session: Database session instance
            openai_client: OpenAI batch client instance
        """
        logger.info("Summary scheduler started")

        while self._running:
            try:
                await self._process_pending_summaries(db_engine, openai_client)
                await asyncio.sleep(self._batch_summary_interval)
            except asyncio.CancelledError:
                logger.info("Summary scheduler cancelled")
                break
            except Exception as e:
                logger.error(f"Error in summary scheduler: {e}")
                await asyncio.sleep(60)  # Wait 1 minute before retrying

    async def _fetch_scheduler(
        self, db_engine: Engine, openai_client: UnifiedOpenAIClient
    ) -> None:
        """Scheduler for fetching batch results.

        Args:
            db_session: Database session instance
            openai_client: OpenAI batch client instance
        """
        logger.info("Fetch scheduler started")

        while self._running:
            try:
                await self._process_active_batches(db_engine, openai_client)
                await asyncio.sleep(self._batch_fetch_interval)
            except asyncio.CancelledError:
                logger.info("Fetch scheduler cancelled")
                break
            except Exception as e:
                logger.error(f"Error in fetch scheduler: {e}")
                await asyncio.sleep(60)  # Wait 1 minute before retrying

    async def _process_pending_summaries(
        self, db_engine: Engine, openai_client: UnifiedOpenAIClient
    ) -> None:
        """Process pending summaries and create batch requests.

        Args:
            db_session: Database session instance
            openai_client: OpenAI batch client instance
        """
        try:
            # Get pending summaries with batch size limit
            pending_papers = self._state_manager.get_pending_summaries(
                db_engine, limit=self._batch_max_items
            )

            if not pending_papers:
                logger.warning("No pending summaries to process")
                return

            # Check daily limit
            if not await self._check_daily_limit(db_engine):
                logger.warning("Daily batch limit reached, skipping summary processing")
                return

            logger.info(f"Processing {len(pending_papers)} pending summaries")

            # Use Paper objects directly
            paper_ids = []

            for paper in pending_papers:
                if paper.paper_id is None:  # Skip papers without ID
                    continue
                paper_ids.append(paper.paper_id)
            self._state_manager.mark_papers_processing(db_engine, paper_ids)

            # Create batch request
            await self._create_batch_request(db_engine, pending_papers, openai_client)

        except Exception as e:
            logger.error(f"Error processing pending summaries: {e}")

    async def _create_batch_request(
        self,
        db_engine: Engine,
        papers: list[Paper],
        openai_client: UnifiedOpenAIClient,
    ) -> None:
        """Create a batch request for paper summarization.

        Args:
            db_engine: Database engine instance
            papers: List of papers to summarize
            openai_client: OpenAI client instance
        """
        # Limit papers to batch_max_items
        papers = papers[: self._batch_max_items]

        # Create batch request payload
        batch_payload = self._create_batch_payload(papers, openai_client)

        # Upload data to OpenAI
        file_id = await openai_client.upload_data(
            batch_payload.to_jsonl(), "batch_requests.jsonl", purpose="batch"
        )

        batch_response = await openai_client.create_batch_request(
            input_file_id=file_id,
            completion_window="24h",
            endpoint="/v1/chat/completions",
        )

        # Store batch record in database
        if not batch_response.id:
            raise RuntimeError("Batch response missing ID")

        self._state_manager.create_batch_record(
            db_engine,
            batch_id=batch_response.id,
            input_file_id=file_id,
            entity_count=len(papers),
            completion_window="24h",
            endpoint="/v1/chat/completions",
        )

        logger.info(
            f"Created batch request {batch_response.id} for {len(papers)} papers"
        )

    def _create_batch_payload(
        self, papers: list[Paper], openai_client: UnifiedOpenAIClient
    ) -> BatchRequestPayload:
        """Create batch request payload using unified prompt structure.

        Args:
            papers: List of papers to include in batch

        Returns:
            Batch request payload
        """

        requests = []

        for paper in papers:
            # Create messages for this paper
            messages = self._summary_service._create_summarization_messages(
                paper.abstract,
                interests=self._interests,
                language=self._language,
            )

            # Create tools if needed
            tools = None
            tool_choice = None
            if openai_client.use_tools:
                tools = [
                    self._summary_service._create_paper_analysis_tool(self._language)
                ]
                tool_choice = self._summary_service._create_tool_choice()

            # Create request data
            request_data = {
                "custom_id": str(paper.paper_id),
                "messages": messages,
                "tools": tools,
                "tool_choice": tool_choice,
            }
            requests.append(request_data)

        return UnifiedBatchBuilder.create_batch_from_requests(
            requests,
            model=openai_client.model,
        )

    async def _process_active_batches(
        self, db_engine: Engine, openai_client: UnifiedOpenAIClient
    ) -> None:
        """Process active batch requests and fetch results.

        Args:
            db_session: Database session instance
        """
        try:
            # Get active batches
            active_batches = self._state_manager.get_active_batches(db_engine)

            if not active_batches:
                logger.warning("No active batches to process")
                return

            logger.info(f"Processing {len(active_batches)} active batches")

            # Process each active batch
            for batch in active_batches:
                await self._process_batch_status(
                    db_engine, batch.model_dump(), openai_client
                )

        except Exception as e:
            logger.error(f"Error processing active batches: {e}")

    async def _process_batch_status(
        self,
        db_engine: Engine,
        batch: dict[str, Any],
        openai_client: UnifiedOpenAIClient,
    ) -> None:
        """Process status of a single batch.

        Args:
            db_session: Database manager instance
            batch: Batch information from database
        """
        try:
            batch_id = batch["batch_id"]

            # Get current status from OpenAI with tracking

            batch_status = await openai_client.get_batch_status(batch_id)

            # Update batch status in database
            self._state_manager.update_batch_status(
                db_engine,
                batch_id=batch_id,
                status=batch_status.status,
                error_file_id=batch_status.error_file_id,
            )

            # If batch is completed, process results
            if batch_status.status == "completed" and batch_status.output_file_id:
                await self._process_batch_results(
                    db_engine, batch_id, batch_status.output_file_id, openai_client
                )

            # If batch failed, log error
            elif batch_status.status == "failed":
                logger.error(f"Batch {batch_id} failed")
                if batch_status.error_file_id:
                    await self._process_batch_errors(
                        db_engine, batch_id, batch_status.error_file_id, openai_client
                    )

            logger.info(f"Updated batch {batch_id} status to {batch_status.status}")

        except Exception as e:
            logger.error(
                f"Error processing batch {batch.get('batch_id', 'unknown')}: {e}"
            )

    async def _process_batch_results(
        self,
        db_engine: Engine,
        batch_id: str,
        output_file_id: str,
        openai_client: UnifiedOpenAIClient,
    ) -> None:
        """Process completed batch results.

        Args:
            db_session: Database manager instance
            batch_id: ID of the completed batch
            output_file_id: ID of the output file
        """
        try:
            # Download output file
            output_file_path = tempfile.mktemp(suffix=".jsonl")
            await openai_client.download_file(output_file_id, output_file_path)

            # Process each result
            with open(output_file_path) as f:
                for line in f:
                    if line.strip():
                        result = json.loads(line)
                        await self._process_single_result(db_engine, batch_id, result)

            # Clean up
            Path(output_file_path).unlink(missing_ok=True)

            logger.info(f"Processed results for batch {batch_id}")

        except Exception as e:
            logger.error(f"Error processing batch results for {batch_id}: {e}")

    async def _process_single_result(
        self, db_engine: Engine, batch_id: str, result: BatchResult
    ) -> None:
        """Process a single batch result.

        Args:
            db_session: Database manager instance
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
                logger.info(f"Processed successful result for paper {paper_id}")
            else:
                # Handle failed result
                error_message = (
                    result.response.get("body", {})
                    .get("error", {})
                    .get("message", "Unknown error")
                )

                logger.warning(f"Failed result for paper {paper_id}: {error_message}")

        except Exception as e:
            logger.error(f"Error processing single result for batch {batch_id}: {e}")

    async def _process_batch_errors(
        self,
        db_engine: Engine,
        batch_id: str,
        error_file_id: str,
        openai_client: UnifiedOpenAIClient,
    ) -> None:
        """Process batch error file.

        Args:
            db_session: Database manager instance
            batch_id: ID of the batch
            error_file_id: ID of the error file
        """
        try:
            # Download error file
            error_file_path = tempfile.mktemp(suffix=".jsonl")
            await openai_client.download_file(error_file_id, error_file_path)

            # Log errors
            with open(error_file_path) as f:
                for line in f:
                    if line.strip():
                        error = json.loads(line)
                        logger.error(f"Batch {batch_id} error: {error}")

            # Clean up
            Path(error_file_path).unlink(missing_ok=True)

        except Exception as e:
            logger.error(f"Error processing batch errors for {batch_id}: {e}")

    async def _check_daily_limit(self, db_engine: Engine) -> bool:
        """Check if daily batch limit has been reached.

        Args:
            db_engine: Database engine instance

        Returns:
            True if under daily limit, False otherwise
        """
        try:
            return self._state_manager.check_daily_batch_limit(
                db_engine, self._batch_daily_limit
            )
        except Exception as e:
            logger.error(f"Error checking daily limit: {e}")
            # On error, be conservative and return False
            return False

    @property
    def is_running(self) -> bool:
        """Check if background manager is running."""
        return self._running

    async def trigger_processing(
        self,
        db_engine: Engine,
        openai_client: UnifiedOpenAIClient,
    ) -> None:
        """Manually trigger batch processing.

        Args:
            db_session: Database manager instance
            openai_client: OpenAI batch client instance
        """
        await self._process_pending_summaries(db_engine, openai_client)
