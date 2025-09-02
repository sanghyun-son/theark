"""Batch management router."""

from fastapi import APIRouter, Depends, HTTPException
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
    BatchItemsResponse,
    BatchListResponse,
    BatchStatusResponse,
    PendingSummariesResponse,
)

router = APIRouter(prefix="/batch", tags=["batch"])


@router.get("/status")
async def get_batch_status() -> BatchStatusResponse:
    """Get overall batch processing status."""
    try:
        # Temporarily return hardcoded response for testing
        return BatchStatusResponse(
            pending_summaries=0,
            active_batches=0,
            batch_details=[],
            message="Batch status retrieved successfully",
        )
    except Exception as e:
        import traceback

        error_detail = f"Failed to get batch status: {str(e)}\n{traceback.format_exc()}"
        raise HTTPException(status_code=500, detail=error_detail)


@router.get("/batches")
async def list_batches(
    db_engine: Engine = Depends(get_engine),
) -> BatchListResponse:
    """List all batch requests."""
    try:
        state_manager = BatchStateManager()
        active_batches = state_manager.get_active_batches(db_engine)

        return BatchListResponse(
            batches=active_batches, message="Batch list retrieved successfully"
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to list batches: {str(e)}")


@router.get("/batches/{batch_id}")
async def get_batch_details(
    batch_id: str,
    db_engine: Engine = Depends(get_engine),
) -> BatchDetailsResponse:
    """Get details of a specific batch."""
    try:
        state_manager = BatchStateManager()
        active_batches = state_manager.get_active_batches(db_engine)

        # Find the specific batch
        batch = next((b for b in active_batches if b["batch_id"] == batch_id), None)
        if not batch:
            raise HTTPException(status_code=404, detail=f"Batch {batch_id} not found")

        # Get batch items
        batch_items = state_manager.get_batch_items(db_engine, batch_id)

        return BatchDetailsResponse(
            batch=batch,
            items=batch_items,
            message="Batch details retrieved successfully",
        )
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=500, detail=f"Failed to get batch details: {str(e)}"
        )


@router.get("/batches/{batch_id}/items")
async def get_batch_items(
    batch_id: str,
    db_engine: Engine = Depends(get_engine),
) -> BatchItemsResponse:
    """Get items for a specific batch."""
    try:
        state_manager = BatchStateManager()
        batch_items = state_manager.get_batch_items(db_engine, batch_id)

        return BatchItemsResponse(
            batch_id=batch_id,
            items=batch_items,
            message="Batch items retrieved successfully",
        )
    except Exception as e:
        raise HTTPException(
            status_code=500, detail=f"Failed to get batch items: {str(e)}"
        )


@router.post("/batches/{batch_id}/cancel")
async def cancel_batch(
    batch_id: str,
    db_engine: Engine = Depends(get_engine),
) -> BatchActionResponse:
    """Cancel a batch request."""
    try:
        # Update batch status to cancelled
        state_manager = BatchStateManager()
        state_manager.update_batch_status(
            db_engine,
            batch_id=batch_id,
            status="cancelled",
        )

        return BatchActionResponse(
            message=f"Batch {batch_id} cancelled successfully",
            batch_id=batch_id,
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to cancel batch: {str(e)}")


@router.get("/pending-summaries")
async def get_pending_summaries(
    db_engine: Engine = Depends(get_engine),
) -> PendingSummariesResponse:
    """Get papers that need summarization."""
    try:
        state_manager = BatchStateManager()
        pending_papers = state_manager.get_pending_summaries(db_engine)

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
    except Exception as e:
        raise HTTPException(
            status_code=500, detail=f"Failed to get pending summaries: {str(e)}"
        )


@router.post("/trigger-processing")
async def trigger_batch_processing(
    db_engine: Engine = Depends(get_engine),
    batch_manager: BackgroundBatchManager = Depends(get_background_batch_manager),
    openai_client: UnifiedOpenAIClient = Depends(get_openai_client),
) -> BatchActionResponse:
    """Manually trigger batch processing."""
    try:
        # Trigger processing of pending summaries
        await batch_manager.trigger_processing(db_engine, openai_client)

        return BatchActionResponse(
            message="Batch processing triggered successfully", batch_id=None
        )
    except Exception as e:
        raise HTTPException(
            status_code=500, detail=f"Failed to trigger batch processing: {str(e)}"
        )
