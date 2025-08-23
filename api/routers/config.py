"""Configuration router for API settings."""

from fastapi import APIRouter

from core.config import load_settings

router = APIRouter(prefix="/v1/config", tags=["config"])


@router.get("/categories")
async def get_preset_categories():
    """Get preset categories for paper filtering."""
    settings = load_settings()
    return {
        "categories": settings.preset_categories,
        "count": len(settings.preset_categories),
    }
