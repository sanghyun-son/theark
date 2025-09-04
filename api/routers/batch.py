"""Batch management router."""

from fastapi import APIRouter, Depends
from sqlalchemy.engine import Engine

from api.dependencies import (
    get_background_batch_manager,
    get_engine,
    get_openai_client,
)
from core.batch.background_manager import BackgroundBatchManager
from core.batch.state_manager import BatchStateManager
from core.llm.openai_client import UnifiedOpenAIClient
from core.models.batch import (
    BatchActionResponse,
    BatchDetailsResponse,
    BatchInfo,
    BatchListResponse,
    BatchStatusResponse,
    PendingSummariesResponse,
)
from core.models.rows import Paper

router = APIRouter(prefix="/batch", tags=["batch"])


@router.get("/status")
async def get_batch_status() -> BatchStatusResponse:
    """Get overall batch processing status."""
    # Temporarily return hardcoded response for testing
    return BatchStatusResponse(
        pending_summaries=0,
        active_batches=0,
        batch_details=[],
        message="Batch status retrieved successfully",
    )


@router.get("/batches")
async def list_batches(
    db_engine: Engine = Depends(get_engine),
) -> BatchListResponse:
    """List all batch requests."""
    from api.utils.error_handler import handle_async_api_operation

    async def get_batches() -> list[BatchInfo]:
        state_manager = BatchStateManager()
        return state_manager.get_active_batches(db_engine)

    active_batches = await handle_async_api_operation(
        get_batches, "Failed to list batches"
    )

    return BatchListResponse(
        batches=active_batches, message="Batch list retrieved successfully"
    )


@router.get("/batches/{batch_id}")
async def get_batch_details(
    batch_id: str,
    db_engine: Engine = Depends(get_engine),
) -> BatchDetailsResponse:
    """Get details of a specific batch."""
    from api.utils.error_handler import handle_async_api_operation

    async def get_batch() -> BatchInfo:
        state_manager = BatchStateManager()
        active_batches = state_manager.get_active_batches(db_engine)

        # Find the specific batch
        batch = next((b for b in active_batches if b.batch_id == batch_id), None)
        if not batch:
            raise ValueError(f"Batch {batch_id} not found")

        return batch

    batch = await handle_async_api_operation(
        get_batch, "Failed to get batch details", f"Batch {batch_id} not found"
    )

    return BatchDetailsResponse(
        batch=batch,
        message="Batch details retrieved successfully",
    )


@router.post("/batches/{batch_id}/cancel")
async def cancel_batch(
    batch_id: str,
    db_engine: Engine = Depends(get_engine),
) -> BatchActionResponse:
    """Cancel a batch request."""
    from api.utils.error_handler import handle_async_api_operation

    async def cancel_batch_operation() -> bool:
        # Update batch status to cancelled
        state_manager = BatchStateManager()
        state_manager.update_batch_status(
            db_engine,
            batch_id=batch_id,
            status="cancelled",
        )
        return True

    await handle_async_api_operation(
        cancel_batch_operation, f"Failed to cancel batch {batch_id}"
    )

    return BatchActionResponse(
        message=f"Batch {batch_id} cancelled successfully",
        batch_id=batch_id,
    )


@router.get("/pending-summaries")
async def get_pending_summaries(
    db_engine: Engine = Depends(get_engine),
) -> PendingSummariesResponse:
    """Get papers that need summarization."""
    from api.utils.error_handler import handle_async_api_operation

    async def get_pending() -> list[Paper]:
        state_manager = BatchStateManager()
        return state_manager.get_pending_summaries(db_engine)

    pending_papers = await handle_async_api_operation(
        get_pending, "Failed to get pending summaries"
    )

    return PendingSummariesResponse(
        pending_summaries=len(pending_papers),
        papers=[
            {
                "paper_id": paper.paper_id,
                "title": paper.title,
                "arxiv_id": paper.arxiv_id,
                "published_at": paper.published_at,
            }
            for paper in pending_papers[:10]  # Limit to first 10 for display
        ],
        message="Pending summaries retrieved successfully",
    )


@router.post("/trigger-processing")
async def trigger_batch_processing(
    db_engine: Engine = Depends(get_engine),
    batch_manager: BackgroundBatchManager = Depends(get_background_batch_manager),
    openai_client: UnifiedOpenAIClient = Depends(get_openai_client),
) -> BatchActionResponse:
    """Manually trigger batch processing."""
    from api.utils.error_handler import handle_async_api_operation

    async def trigger_processing() -> bool:
        # Trigger processing of pending summaries
        await batch_manager.trigger_processing(db_engine, openai_client)
        return True

    await handle_async_api_operation(
        trigger_processing, "Failed to trigger batch processing"
    )

    return BatchActionResponse(
        message="Batch processing triggered successfully", batch_id=None
    )
