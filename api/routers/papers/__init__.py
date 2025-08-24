"""Papers router package."""

# Combine all routers
from fastapi import APIRouter

from .crud import router as crud_router
from .star import router as star_router
from .summary import router as summary_router

router = APIRouter(prefix="/v1/papers", tags=["papers"])
router.include_router(crud_router)
router.include_router(summary_router)
router.include_router(star_router)
