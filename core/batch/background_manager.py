"""Background batch processing manager."""

import asyncio
import json
import tempfile
import time
from pathlib import Path
from typing import Any

from sqlalchemy.engine import Engine
from sqlmodel import Session

from core.batch.state_manager import BatchStateManager
from core.database.repository import (
    LLMBatchRepository,
    PaperRepository,
    SummaryRepository,
)
from core.llm.batch_builder import UnifiedBatchBuilder
from core.llm.openai_client import UnifiedOpenAIClient
from core.log import get_logger
from core.models.batch import (
    BatchInfo,
    BatchProcessingResult,
    BatchRequestPayload,
    BatchResult,
    BatchStatusInfo,
    BulkProcessingSummary,
)
from core.models.external.openai import ChatCompletionResponse, PaperAnalysis
from core.models.rows import Paper, Summary
from core.services.summarization_service import PaperSummarizationService
from core.types import PaperSummaryStatus

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
            batch_payload.to_jsonl(),
            "batch_requests.jsonl",
            purpose="batch",
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
            db_engine: Database engine instance
            openai_client: OpenAI client instance
        """
        try:
            # Get active batches
            active_batches = self._state_manager.get_active_batches(db_engine)

            if not active_batches:
                logger.warning("No active batches to process")
                return

            logger.info(f"Processing {len(active_batches)} active batches")

            # Use bulk processing for better performance
            await self._process_batches_bulk(db_engine, active_batches, openai_client)

        except Exception as e:
            logger.error(f"Error processing active batches: {e}")

    async def _process_batches_bulk(
        self,
        db_engine: Engine,
        active_batches: list[BatchInfo],
        openai_client: UnifiedOpenAIClient,
    ) -> BulkProcessingSummary:
        """Process multiple batches in bulk for better performance.

        Args:
            db_engine: Database engine instance
            active_batches: List of active batch information
            openai_client: OpenAI client instance

        Returns:
            BulkProcessingSummary with processing results
        """
        logger.info(f"Starting bulk processing of {len(active_batches)} batches")
        start_time = time.time()

        # Step 1: Check all batch statuses
        batch_results = await self._check_batch_statuses_bulk(
            active_batches, openai_client
        )

        # Step 2: Group batches by status for efficient processing
        completed_batches = [
            r for r in batch_results if r.status_info.status == "completed"
        ]
        failed_batches = [r for r in batch_results if r.status_info.status == "failed"]

        # Step 3: Process completed batches in bulk
        if completed_batches:
            logger.info(
                f"Processing {len(completed_batches)} completed batches in bulk"
            )
            await self._process_completed_batches_bulk(
                db_engine, completed_batches, openai_client
            )

        # Step 4: Process failed batches
        if failed_batches:
            logger.info(f"Processing {len(failed_batches)} failed batches")
            await self._process_failed_batches_bulk(
                db_engine, failed_batches, openai_client
            )

        # Step 5: Update all batch statuses in bulk
        await self._update_batch_statuses_bulk(db_engine, batch_results)

        processing_time = time.time() - start_time

        # Create summary
        summary = BulkProcessingSummary(
            total_batches=len(active_batches),
            successful_batches=len([r for r in batch_results if r.success]),
            failed_batches=len([r for r in batch_results if not r.success]),
            total_summaries=sum(len(r.summaries) for r in batch_results),
            processing_time_seconds=processing_time,
            batches_processed=batch_results,
        )

        logger.info(
            f"Bulk processing completed in {processing_time:.2f}s: "
            f"{summary.successful_batches} successful, {summary.failed_batches} failed, "
            f"{summary.total_summaries} summaries created"
        )

        return summary

    async def _check_batch_statuses_bulk(
        self, active_batches: list[BatchInfo], openai_client: UnifiedOpenAIClient
    ) -> list[BatchProcessingResult]:
        """Check status of multiple batches concurrently.

        Args:
            active_batches: List of active batch information
            openai_client: OpenAI client instance

        Returns:
            List of BatchProcessingResult objects
        """

        async def check_single_batch(batch_info: BatchInfo) -> BatchProcessingResult:
            try:
                status = await openai_client.get_batch_status(batch_info.batch_id)

                # Convert status to BatchStatusInfo
                created_at = getattr(status, "created_at", None)
                completed_at = getattr(status, "completed_at", None)

                # Convert timestamps to strings if they are integers
                if isinstance(created_at, int):
                    created_at = str(created_at)
                if isinstance(completed_at, int):
                    completed_at = str(completed_at)

                status_info = BatchStatusInfo(
                    batch_id=batch_info.batch_id,
                    status=status.status,
                    output_file_id=getattr(status, "output_file_id", None),
                    error_file_id=getattr(status, "error_file_id", None),
                    created_at=created_at,
                    completed_at=completed_at,
                )

                return BatchProcessingResult(
                    batch_info=batch_info,
                    status_info=status_info,
                    success=True,
                    summaries=[],
                )
            except Exception as e:
                logger.error(
                    f"Error checking status for batch {batch_info.batch_id}: {e}"
                )
                return BatchProcessingResult(
                    batch_info=batch_info,
                    status_info=BatchStatusInfo(
                        batch_id=batch_info.batch_id,
                        status="error",
                        output_file_id=None,
                        error_file_id=None,
                    ),
                    success=False,
                    error_message=str(e),
                    summaries=[],
                )

        # Check all batch statuses concurrently
        tasks = [check_single_batch(batch) for batch in active_batches]
        results = await asyncio.gather(*tasks, return_exceptions=True)

        # Filter out exceptions and build result list
        batch_results = []
        for result in results:
            if isinstance(result, Exception):
                logger.error(f"Exception in batch status check: {result}")
                continue
            if isinstance(result, BatchProcessingResult):
                batch_results.append(result)

        logger.info(f"Checked status for {len(batch_results)} batches")
        return batch_results

    async def _process_completed_batches_bulk(
        self,
        db_engine: Engine,
        completed_batches: list[BatchProcessingResult],
        openai_client: UnifiedOpenAIClient,
    ) -> None:
        """Process multiple completed batches in true bulk.

        Args:
            db_engine: Database engine instance
            completed_batches: List of BatchProcessingResult objects for completed batches
            openai_client: OpenAI client instance
        """
        if not completed_batches:
            return

        logger.info(
            f"Starting true bulk processing of {len(completed_batches)} completed batches"
        )

        # Step 1: Download all result files concurrently
        downloaded_files = await self._download_batch_files_bulk(
            completed_batches, openai_client
        )

        # Step 2: Parse all result files and collect summaries
        all_summaries = []
        batch_summary_mapping = {}

        for batch_result, file_path in downloaded_files:
            if file_path:
                try:
                    summaries = await self._parse_results_file(
                        file_path, batch_result.batch_info.batch_id, db_engine
                    )
                    all_summaries.extend(summaries)
                    batch_summary_mapping[batch_result.batch_info.batch_id] = summaries

                    # Update the batch result with summaries
                    batch_result.summaries = summaries
                    batch_result.success = True
                except Exception as e:
                    logger.error(
                        f"Error parsing results for batch {batch_result.batch_info.batch_id}: {e}"
                    )
                    batch_result.success = False
                    batch_result.error_message = str(e)
                finally:
                    # Clean up downloaded file
                    if Path(file_path).exists():
                        Path(file_path).unlink(missing_ok=True)

        # Step 3: Bulk create all summaries and update papers
        if all_summaries:
            await self._bulk_create_summaries_and_update_papers(
                db_engine, all_summaries, batch_summary_mapping
            )

        logger.info(
            f"Bulk processing completed: {len(all_summaries)} summaries processed"
        )

    async def _download_batch_files_bulk(
        self,
        completed_batches: list[BatchProcessingResult],
        openai_client: UnifiedOpenAIClient,
    ) -> list[tuple[BatchProcessingResult, str | None]]:
        """Download all batch result files concurrently.

        Args:
            completed_batches: List of BatchProcessingResult objects
            openai_client: OpenAI client instance

        Returns:
            List of (BatchProcessingResult, file_path) tuples
        """

        async def download_single_file(
            batch_result: BatchProcessingResult,
        ) -> tuple[BatchProcessingResult, str | None]:
            """Download a single batch result file."""
            try:
                if not batch_result.status_info.output_file_id:
                    logger.warning(
                        f"No output file for batch {batch_result.batch_info.batch_id}"
                    )
                    return batch_result, None

                # Create temporary file
                output_file_path = tempfile.mktemp(suffix=".jsonl")
                await openai_client.download_file(
                    batch_result.status_info.output_file_id, output_file_path
                )
                return batch_result, output_file_path
            except Exception as e:
                logger.error(
                    f"Error downloading file for batch {batch_result.batch_info.batch_id}: {e}"
                )
                return batch_result, None

        # Download all files concurrently
        tasks = [
            download_single_file(batch_result) for batch_result in completed_batches
        ]
        results = await asyncio.gather(*tasks, return_exceptions=True)

        # Filter out exceptions and return valid results
        downloaded_files = []
        for result in results:
            if isinstance(result, Exception):
                logger.error(f"Exception in file download: {result}")
                continue
            if isinstance(result, tuple) and len(result) == 2:
                downloaded_files.append(result)

        logger.info(f"Downloaded {len(downloaded_files)} files concurrently")
        return downloaded_files

    async def _bulk_create_summaries_and_update_papers(
        self,
        db_engine: Engine,
        all_summaries: list[Summary],
        batch_summary_mapping: dict[str, list[Summary]],
    ) -> None:
        """Bulk create summaries and update papers in a single transaction.

        Args:
            db_engine: Database engine instance
            all_summaries: All summaries to create
            batch_summary_mapping: Mapping of batch_id to summaries for metrics
        """
        try:
            with Session(db_engine) as session:
                # Bulk create all summaries
                summary_repo = SummaryRepository(session)
                created_summaries = summary_repo.create_summaries_bulk(all_summaries)
                logger.info(f"Bulk created {len(created_summaries)} summaries")

                # Update papers in bulk
                paper_repo = PaperRepository(session)
                paper_ids = [
                    summary.paper_id
                    for summary in created_summaries
                    if summary.paper_id is not None
                ]
                if paper_ids:
                    updated_count = paper_repo.update_summary_status_bulk(
                        paper_ids, PaperSummaryStatus.DONE
                    )
                    logger.info(f"Bulk updated {updated_count} papers to DONE status")

                # Update batch metrics in bulk
                batch_repo = LLMBatchRepository(session)
                for batch_id, summaries in batch_summary_mapping.items():
                    successful_count = len(summaries)
                    batch_repo.update_batch_status_with_metrics(
                        batch_id,
                        status="completed",
                        successful_count=successful_count,
                        failed_count=0,
                    )

                session.commit()
                logger.info(
                    f"Bulk transaction completed: {len(created_summaries)} summaries, {len(paper_ids)} papers updated"
                )

        except Exception as e:
            logger.error(f"Error in bulk summary creation and paper update: {e}")
            # Session rollback is handled by the context manager

    async def _process_failed_batches_bulk(
        self,
        db_engine: Engine,
        failed_batches: list[BatchProcessingResult],
        openai_client: UnifiedOpenAIClient,
    ) -> None:
        """Process multiple failed batches in bulk.

        Args:
            db_engine: Database engine instance
            failed_batches: List of BatchProcessingResult objects for failed batches
            openai_client: OpenAI client instance
        """

        async def process_single_failed_batch(
            batch_result: BatchProcessingResult,
        ) -> BatchProcessingResult:
            """Process a single failed batch and return updated result."""
            try:
                logger.error(f"Batch {batch_result.batch_info.batch_id} failed")
                if batch_result.status_info.error_file_id:
                    await self._process_batch_errors(
                        db_engine,
                        batch_result.batch_info.batch_id,
                        batch_result.status_info.error_file_id,
                        openai_client,
                    )
                batch_result.success = True
                return batch_result
            except Exception as e:
                logger.error(
                    f"Error processing failed batch {batch_result.batch_info.batch_id}: {e}"
                )
                batch_result.success = False
                batch_result.error_message = str(e)
                return batch_result

        # Process all failed batches concurrently
        tasks = [
            process_single_failed_batch(batch_result) for batch_result in failed_batches
        ]
        results = await asyncio.gather(*tasks, return_exceptions=True)

        # Count successful and failed processing
        successful = sum(
            1
            for result in results
            if isinstance(result, BatchProcessingResult) and result.success
        )
        failed = len(results) - successful
        logger.info(
            f"Bulk failed batch processing: {successful} successful, {failed} failed"
        )

    async def _update_batch_statuses_bulk(
        self, db_engine: Engine, batch_results: list[BatchProcessingResult]
    ) -> None:
        """Update batch statuses in bulk for better database performance.

        Args:
            db_engine: Database engine instance
            batch_results: List of BatchProcessingResult objects
        """
        try:
            with Session(db_engine) as session:

                # Prepare bulk update data
                batch_updates = []
                for batch_result in batch_results:
                    batch_updates.append(
                        {
                            "batch_id": batch_result.batch_info.batch_id,
                            "status": batch_result.status_info.status,
                            "error_file_id": batch_result.status_info.error_file_id,
                        }
                    )

                if not batch_updates:
                    return

                # Execute bulk update using SQLModel's bulk operations
                batch_repo = LLMBatchRepository(session)
                for update_data in batch_updates:
                    batch_id = update_data["batch_id"]
                    status = update_data["status"]
                    error_file_id = update_data["error_file_id"]

                    if batch_id and status:
                        batch_repo.update_batch_status(
                            batch_id,
                            status=status,
                            error_file_id=error_file_id,
                        )

                session.commit()
                logger.info(
                    f"Bulk updated status for {len(batch_updates)} batches in single transaction"
                )

        except Exception as e:
            logger.error(f"Error updating batch statuses in bulk: {e}")

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

            # Early exit: Handle completed batch
            if batch_status.status == "completed" and batch_status.output_file_id:
                await self._process_batch_results(
                    db_engine, batch_id, batch_status.output_file_id, openai_client
                )
                logger.info(f"Updated batch {batch_id} status to {batch_status.status}")
                return

            # Early exit: Handle failed batch
            if batch_status.status == "failed":
                logger.error(f"Batch {batch_id} failed")
                if batch_status.error_file_id:
                    await self._process_batch_errors(
                        db_engine, batch_id, batch_status.error_file_id, openai_client
                    )
                logger.info(f"Updated batch {batch_id} status to {batch_status.status}")
                return

            # Default: Log status update
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
        output_file_path = None
        try:
            # Download output file
            output_file_path = tempfile.mktemp(suffix=".jsonl")
            await openai_client.download_file(output_file_id, output_file_path)

            # Process each result
            await self._process_results_from_file(db_engine, batch_id, output_file_path)

            logger.info(f"Processed results for batch {batch_id}")

        except Exception as e:
            logger.error(f"Error processing batch results for {batch_id}: {e}")
        finally:
            # Clean up file regardless of success/failure
            if output_file_path and Path(output_file_path).exists():
                Path(output_file_path).unlink(missing_ok=True)

    async def _process_results_from_file(
        self, db_engine: Engine, batch_id: str, file_path: str
    ) -> None:
        """Process batch results from a downloaded file.

        Args:
            db_engine: Database engine instance
            batch_id: ID of the batch
            file_path: Path to the downloaded results file
        """
        try:
            summaries_to_create = await self._parse_results_file(
                file_path, batch_id, db_engine
            )
            if not summaries_to_create:
                return

            self._create_summaries_and_update_papers(
                db_engine, summaries_to_create, batch_id
            )

        except FileNotFoundError:
            logger.error(f"Results file not found for batch {batch_id}: {file_path}")
        except Exception as e:
            logger.error(f"Error reading results file for batch {batch_id}: {e}")

    async def _parse_results_file(
        self, file_path: str, batch_id: str, db_engine: Engine
    ) -> list[Summary]:
        """Parse the results file and extract summaries to create."""
        summaries_to_create = []

        with open(file_path) as f:
            for line_num, line in enumerate(f, 1):
                if not line.strip():
                    continue

                summary = await self._parse_single_line(
                    line, line_num, batch_id, db_engine
                )
                if summary:
                    summaries_to_create.append(summary)

        return summaries_to_create

    async def _parse_single_line(
        self, line: str, line_num: int, batch_id: str, db_engine: Engine
    ) -> Summary | None:
        """Parse a single line from the results file."""
        try:
            result_data = json.loads(line)
            result = BatchResult(
                custom_id=result_data.get("custom_id"),
                status_code=result_data.get("status_code", 200),
                response=result_data.get("response", {}),
                error=result_data.get("error"),
            )

            result_success, summary = await self._process_single_result(
                db_engine, batch_id, result
            )
            return summary if result_success else None

        except json.JSONDecodeError as e:
            logger.warning(f"Failed to parse line {line_num} in batch {batch_id}: {e}")
        except Exception as e:
            logger.error(f"Error processing line {line_num} in batch {batch_id}: {e}")

        return None

    def _create_summaries_and_update_papers(
        self, db_engine: Engine, summaries_to_create: list[Summary], batch_id: str
    ) -> None:
        """Create summaries and update paper statuses in bulk."""
        try:
            with Session(db_engine) as session:
                summary_repo = SummaryRepository(session)
                created_summaries = summary_repo.create_summaries_bulk(
                    summaries_to_create
                )

                if not created_summaries:
                    logger.info("No summaries were created from file")
                    return

                # Update paper statuses to DONE in bulk
                paper_ids = [
                    s.paper_id for s in created_summaries if s.paper_id is not None
                ]

                if paper_ids:
                    paper_repo = PaperRepository(session)
                    paper_repo.update_summary_status_bulk(
                        paper_ids, PaperSummaryStatus.DONE
                    )

                logger.info(
                    f"Created {len(created_summaries)} summaries in bulk from file"
                )
        except Exception as e:
            logger.error(f"Error in bulk summary creation from file: {e}")
            # Just ignore failures as requested
            pass

    def _create_summaries_and_update_papers_direct(
        self, db_engine: Engine, summaries_to_create: list[Summary]
    ) -> None:
        """Create summaries and update paper statuses in bulk for direct processing."""
        try:
            with Session(db_engine) as session:
                summary_repo = SummaryRepository(session)
                created_summaries = summary_repo.create_summaries_bulk(
                    summaries_to_create
                )

                if not created_summaries:
                    logger.info("No summaries were created in bulk")
                    return

                # Update paper statuses to DONE in bulk
                paper_ids = [
                    s.paper_id for s in created_summaries if s.paper_id is not None
                ]

                if paper_ids:
                    paper_repo = PaperRepository(session)
                    paper_repo.update_summary_status_bulk(
                        paper_ids, PaperSummaryStatus.DONE
                    )

                logger.info(f"Created {len(created_summaries)} summaries in bulk")
        except Exception as e:
            logger.error(f"Error in bulk summary creation: {e}")
            # Just ignore failures as requested
            pass

    async def _process_batch_results_direct(
        self,
        db_engine: Engine,
        batch_id: str,
        results: list[BatchResult],
    ) -> None:
        """Process batch results directly from BatchResult objects.

        Args:
            db_engine: Database engine instance
            batch_id: ID of the batch
            results: List of batch results to process
        """
        # Process each result and collect any system errors
        system_errors = []
        successful_count = 0
        failed_count = 0

        # Process results and collect summaries for bulk creation
        summaries_to_create = []

        for result in results:
            try:
                result_success, summary = await self._process_single_result(
                    db_engine, batch_id, result
                )
                if result_success and summary:
                    summaries_to_create.append(summary)
                    successful_count += 1
                else:
                    failed_count += 1
            except Exception as e:
                # This is a system-level error, collect it
                system_errors.append(e)
                logger.error(
                    f"System error processing result for batch {batch_id}: {e}"
                )

        # Create summaries in bulk if any exist
        if summaries_to_create:
            self._create_summaries_and_update_papers_direct(
                db_engine, summaries_to_create
            )

        # Update batch status based on whether system errors occurred
        if system_errors:
            self._update_batch_status(db_engine, batch_id, "error")
            logger.error(
                f"Batch {batch_id} marked as error due to {len(system_errors)} system-level failures"
            )
        else:
            self._update_batch_status_with_metrics(
                db_engine, batch_id, "completed", successful_count, failed_count
            )
            logger.info(
                f"Processed {len(results)} results for batch {batch_id} ({successful_count} successful, {failed_count} failed)"
            )

    def _update_batch_status(
        self, db_engine: Engine, batch_id: str, status: str
    ) -> None:
        """Update batch status in database.

        Args:
            db_engine: Database engine instance
            batch_id: ID of the batch to update
            status: New status to set
        """
        try:
            with Session(db_engine) as session:
                batch_repo = LLMBatchRepository(session)
                batch_repo.update_batch_status(batch_id, status)
        except Exception as e:
            logger.error(f"Failed to update batch {batch_id} status to {status}: {e}")

    def _update_batch_status_with_metrics(
        self,
        db_engine: Engine,
        batch_id: str,
        status: str,
        successful_count: int,
        failed_count: int,
    ) -> None:
        """Update batch status and metrics in database.

        Args:
            db_engine: Database engine instance
            batch_id: ID of the batch to update
            status: New status to set
            successful_count: Number of successfully processed results
            failed_count: Number of failed results
        """
        try:
            with Session(db_engine) as session:
                batch_repo = LLMBatchRepository(session)
                batch_repo.update_batch_status_with_metrics(
                    batch_id, status, successful_count, failed_count
                )
        except Exception as e:
            logger.error(
                f"Failed to update batch {batch_id} status to {status} with metrics: {e}"
            )

    async def _process_single_result(
        self, db_engine: Engine, batch_id: str, result: BatchResult
    ) -> tuple[bool, Summary | None]:
        """Process a single batch result.

        Args:
            db_engine: Database engine instance
            batch_id: ID of the batch
            result: Single result from batch

        Returns:
            Tuple of (success_status, summary_object)
        """
        try:
            paper_id = self._extract_paper_id(result)
            if not paper_id:
                # This is a paper-level issue, not a system error
                logger.warning(f"Invalid paper ID in result: {result}")
                return False, None

            if not self._is_successful_result(result, paper_id):
                # This is a paper-level issue, not a system error
                return False, None

            summary = self._create_summary_from_response(result, paper_id)
            if summary:
                return True, summary

            return False, None

        except (ValueError, TypeError) as e:
            # These are paper-level parsing errors, not system errors
            logger.warning(
                f"Paper-level error processing result for batch {batch_id}: {e}"
            )
            return False, None
        except Exception as e:
            # This is a system-level error, re-raise it
            logger.error(
                f"System error processing single result for batch {batch_id}: {e}"
            )
            raise

    def _extract_paper_id(self, result: BatchResult) -> int | None:
        """Extract paper ID from batch result."""
        custom_id = result.custom_id
        if not custom_id:
            logger.warning(f"No custom_id in batch result: {result}")
            return None
        return int(custom_id)

    def _is_successful_result(self, result: BatchResult, paper_id: int) -> bool:
        """Check if batch result was successful."""
        if result.status_code == 200:
            return True

        error_message = (
            result.response.get("body", {})
            .get("error", {})
            .get("message", "Unknown error")
        )
        logger.warning(f"Failed result for paper {paper_id}: {error_message}")
        return False

    def _create_summary_from_response(
        self, result: BatchResult, paper_id: int
    ) -> Summary | None:
        """Create Summary object from OpenAI response."""
        try:
            response_body = result.response.get("body", {})
            chat_response = ChatCompletionResponse.model_validate(response_body)

            if not self._has_valid_tool_calls(chat_response):
                logger.warning(f"No tool calls found in response for paper {paper_id}")
                return None

            # At this point, we know choices[0] and tool_calls exist
            first_choice = chat_response.choices[0]
            if not first_choice.message.tool_calls:
                logger.warning(f"No tool calls found in response for paper {paper_id}")
                return None

            tool_call = first_choice.message.tool_calls[0]
            paper_analysis = PaperAnalysis.from_json_string(
                tool_call.function.arguments
            )

            return self._build_summary_from_analysis(
                paper_analysis, paper_id, chat_response.model
            )

        except Exception as e:
            logger.error(f"Error creating summary for paper {paper_id}: {e}")
            return None

    def _has_valid_tool_calls(self, chat_response: ChatCompletionResponse) -> bool:
        """Check if chat response has valid tool calls."""
        return bool(
            chat_response.choices and chat_response.choices[0].message.tool_calls
        )

    def _build_summary_from_analysis(
        self, paper_analysis: PaperAnalysis, paper_id: int, model: str
    ) -> Summary:
        """Build Summary object from paper analysis."""
        return Summary(
            paper_id=paper_id,
            version="1.0",
            overview=paper_analysis.tldr,
            motivation=paper_analysis.motivation,
            method=paper_analysis.method,
            result=paper_analysis.result,
            conclusion=paper_analysis.conclusion,
            language=self._language,
            interests="",
            relevance=paper_analysis.relevance,
            model=model,
        )

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
        error_file_path = None
        try:
            # Download error file
            error_file_path = tempfile.mktemp(suffix=".jsonl")
            await openai_client.download_file(error_file_id, error_file_path)

            # Log errors
            await self._log_errors_from_file(batch_id, error_file_path)

        except Exception as e:
            logger.error(f"Error processing batch errors for {batch_id}: {e}")
        finally:
            # Clean up file regardless of success/failure
            if error_file_path and Path(error_file_path).exists():
                Path(error_file_path).unlink(missing_ok=True)

    async def _log_errors_from_file(self, batch_id: str, file_path: str) -> None:
        """Log errors from a downloaded error file.

        Args:
            batch_id: ID of the batch
            file_path: Path to the downloaded error file
        """
        try:
            with open(file_path) as f:
                for line_num, line in enumerate(f, 1):
                    if not line.strip():
                        continue

                    try:
                        error = json.loads(line)
                        logger.error(
                            f"Batch {batch_id} error (line {line_num}): {error}"
                        )
                    except json.JSONDecodeError as e:
                        logger.warning(
                            f"Failed to parse error line {line_num} in batch {batch_id}: {e}"
                        )
                        continue
        except FileNotFoundError:
            logger.error(f"Error file not found for batch {batch_id}: {file_path}")
        except Exception as e:
            logger.error(f"Error reading error file for batch {batch_id}: {e}")

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
