"""Statistics API router."""

from typing import Annotated

from fastapi import APIRouter, Depends
from sqlmodel import Session

from api.dependencies import get_db
from core.models.api.responses import StatisticsResponse
from core.services.statistics_service import StatisticsService

router = APIRouter(prefix="/v1", tags=["statistics"])


@router.get("/statistics", response_model=StatisticsResponse)
async def get_statistics(db: Annotated[Session, Depends(get_db)]) -> StatisticsResponse:
    """Get application statistics.

    Returns:
        Comprehensive application statistics including paper counts and summary coverage
    """
    statistics_service = StatisticsService(db)
    return statistics_service.get_application_statistics()
