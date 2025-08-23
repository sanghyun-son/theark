"""Configuration router for API settings."""

from fastapi import APIRouter

from api.models.config import CategoriesResponse
from core.config import load_settings

router = APIRouter(prefix="/v1/config", tags=["config"])


@router.get("/categories", response_model=CategoriesResponse)
async def get_preset_categories() -> CategoriesResponse:
    """Get preset categories for paper filtering."""
    settings = load_settings()
    return CategoriesResponse(
        categories=settings.preset_categories,
        count=len(settings.preset_categories),
    )
