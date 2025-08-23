"""Configuration router for API settings."""

from fastapi import APIRouter

from core.config import load_settings
from core.models import CategoriesResponse

router = APIRouter(prefix="/v1/config", tags=["config"])


@router.get("/categories", response_model=CategoriesResponse)
async def get_preset_categories() -> CategoriesResponse:
    """Get preset categories for paper filtering."""
    settings = load_settings()
    return CategoriesResponse(
        categories=settings.preset_categories,
        count=len(settings.preset_categories),
    )
