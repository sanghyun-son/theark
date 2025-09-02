"""API router for crawler operations."""

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.engine import Engine

from api.dependencies import get_arxiv_explorer, get_crawl_service, get_engine
from core.extractors.concrete.arxiv_source_explorer import ArxivSourceExplorer
from core.log import get_logger
from core.models.api.responses import (
    CrawlerProgressResponse,
    CrawlerResponse,
    CrawlerStatusResponse,
)
from core.services.crawl_service import CrawlService

logger = get_logger(__name__)

router = APIRouter(prefix="/v1/crawler", tags=["crawler"])


@router.put("", response_model=CrawlerResponse)
async def start_crawler(
    crawl_service: CrawlService = Depends(get_crawl_service),
    explorer: ArxivSourceExplorer = Depends(get_arxiv_explorer),
    engine: Engine = Depends(get_engine),
) -> CrawlerResponse:
    """Start or restart crawler."""

    if crawl_service.is_running(engine):
        return CrawlerResponse(
            status="running",
            message="Crawler is already running",
            was_already_running=True,
        )

    try:
        if await crawl_service.start_crawling(explorer, engine):
            return CrawlerResponse(
                status="running",
                message="Crawler is now running",
                was_already_running=False,
            )
        else:
            raise HTTPException(status_code=500, detail="Failed to start crawler")

    except Exception as e:
        logger.error(f"Error starting crawler: {e}")
        raise HTTPException(
            status_code=500, detail=f"Failed to start crawler: {str(e)}"
        )


@router.delete("", response_model=CrawlerResponse)
async def stop_crawler(
    crawl_service: CrawlService = Depends(get_crawl_service),
) -> CrawlerResponse:
    """Stop crawler."""
    try:
        if await crawl_service.stop_crawling():
            return CrawlerResponse(
                status="stopped",
                message="Crawler stopped successfully",
            )
        else:
            raise HTTPException(status_code=500, detail="Failed to stop crawler")
    except Exception as e:
        logger.error(f"Error stopping crawler: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to stop crawler: {str(e)}")


@router.get("", response_model=CrawlerStatusResponse)
async def get_crawler_status(
    crawl_service: CrawlService = Depends(get_crawl_service),
    engine: Engine = Depends(get_engine),
) -> CrawlerStatusResponse:
    """Get crawler status."""
    try:
        status = crawl_service.get_status(engine)
        return CrawlerStatusResponse(
            is_running=crawl_service.is_running(engine),
            is_active=status.is_active,
            current_date=status.current_date,
            current_category_index=status.current_category_index,
            categories=status.categories,
        )
    except Exception as e:
        logger.error(f"Error getting crawler status: {e}")
        raise HTTPException(
            status_code=500, detail=f"Failed to get crawler status: {str(e)}"
        )


@router.get("/progress", response_model=CrawlerProgressResponse)
async def get_crawler_progress(
    crawl_service: CrawlService = Depends(get_crawl_service),
    engine: Engine = Depends(get_engine),
) -> CrawlerProgressResponse:
    """Get crawler progress."""
    try:
        progress = crawl_service.get_progress(engine)
        return CrawlerProgressResponse(
            total_papers_found=progress.total_papers_found,
            total_papers_stored=progress.total_papers_stored,
            completed_date_categories=progress.completed_date_categories,
            failed_date_categories=progress.failed_date_categories,
        )
    except Exception as e:
        logger.error(f"Error getting crawler progress: {e}")
        raise HTTPException(
            status_code=500, detail=f"Failed to get crawler progress: {str(e)}"
        )
