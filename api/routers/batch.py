"""Batch management router."""

from fastapi import APIRouter, HTTPException

from api.dependencies import BatchManager, DBManager, OpenAIBatchClientDep
from core.batch.state_manager import BatchStateManager
from core.models.batch import (
    BatchActionResponse,
    BatchDetailsResponse,
    BatchItemsResponse,
    BatchListResponse,
    BatchStatusResponse,
    PendingSummariesResponse,
)

router = APIRouter(prefix="/batch", tags=["batch"])


@router.get("/status")
async def get_batch_status(db_manager: DBManager) -> BatchStatusResponse:
    """Get overall batch processing status."""
    try:
        state_manager = BatchStateManager()

        # Get pending summaries count
        pending_papers = await state_manager.get_pending_summaries(db_manager)

        # Get active batches
        active_batches = await state_manager.get_active_batches(db_manager)

        return BatchStatusResponse(
            pending_summaries=len(pending_papers),
            active_batches=len(active_batches),
            batch_details=[
                {
                    "batch_id": batch["batch_id"],
                    "status": batch["status"],
                    "created_at": batch["created_at"],
                    "completion_window": batch["completion_window"],
                }
                for batch in active_batches
            ],
        )
    except Exception as e:
        raise HTTPException(
            status_code=500, detail=f"Failed to get batch status: {str(e)}"
        )


@router.get("/batches")
async def list_batches(db_manager: DBManager) -> BatchListResponse:
    """List all batch requests."""
    try:
        state_manager = BatchStateManager()
        active_batches = await state_manager.get_active_batches(db_manager)

        return BatchListResponse(batches=active_batches)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to list batches: {str(e)}")


@router.get("/batches/{batch_id}")
async def get_batch_details(
    batch_id: str, db_manager: DBManager
) -> BatchDetailsResponse:
    """Get details of a specific batch."""
    try:
        state_manager = BatchStateManager()
        active_batches = await state_manager.get_active_batches(db_manager)

        # Find the specific batch
        batch = next((b for b in active_batches if b["batch_id"] == batch_id), None)
        if not batch:
            raise HTTPException(status_code=404, detail=f"Batch {batch_id} not found")

        # Get batch items
        batch_items = await state_manager.get_batch_items(db_manager, batch_id)

        return BatchDetailsResponse(batch=batch, items=batch_items)
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=500, detail=f"Failed to get batch details: {str(e)}"
        )


@router.get("/batches/{batch_id}/items")
async def get_batch_items(batch_id: str, db_manager: DBManager) -> BatchItemsResponse:
    """Get items for a specific batch."""
    try:
        state_manager = BatchStateManager()
        batch_items = await state_manager.get_batch_items(db_manager, batch_id)

        return BatchItemsResponse(batch_id=batch_id, items=batch_items)
    except Exception as e:
        raise HTTPException(
            status_code=500, detail=f"Failed to get batch items: {str(e)}"
        )


@router.post("/batches/{batch_id}/cancel")
async def cancel_batch(
    batch_id: str, db_manager: DBManager, batch_manager: BatchManager
) -> BatchActionResponse:
    """Cancel a batch request."""
    try:
        # Update batch status to cancelled
        state_manager = BatchStateManager()
        await state_manager.update_batch_status(
            db_manager, batch_id=batch_id, status="cancelled"
        )

        return BatchActionResponse(
            message=f"Batch {batch_id} cancelled successfully",
            batch_id=batch_id,
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to cancel batch: {str(e)}")


@router.get("/pending-summaries")
async def get_pending_summaries(db_manager: DBManager) -> PendingSummariesResponse:
    """Get papers that need summarization."""
    try:
        state_manager = BatchStateManager()
        pending_papers = await state_manager.get_pending_summaries(db_manager)

        return PendingSummariesResponse(
            pending_summaries=len(pending_papers),
            papers=[
                {
                    "paper_id": paper["paper_id"],
                    "title": paper["title"],
                    "arxiv_id": paper["arxiv_id"],
                    "published_at": paper["published_at"],
                }
                for paper in pending_papers[:10]  # Limit to first 10 for display
            ],
        )
    except Exception as e:
        raise HTTPException(
            status_code=500, detail=f"Failed to get pending summaries: {str(e)}"
        )


@router.post("/trigger-processing")
async def trigger_batch_processing(
    db_manager: DBManager,
    batch_manager: BatchManager,
    openai_client: OpenAIBatchClientDep,
) -> BatchActionResponse:
    """Manually trigger batch processing."""
    try:
        # Trigger processing of pending summaries
        await batch_manager.trigger_processing(db_manager, openai_client)

        return BatchActionResponse(
            message="Batch processing triggered successfully", batch_id=None
        )
    except Exception as e:
        raise HTTPException(
            status_code=500, detail=f"Failed to trigger batch processing: {str(e)}"
        )
