"""API routers package."""

from .common import router as common_router
from .papers import router as papers_router

__all__ = ["common_router", "papers_router"]
