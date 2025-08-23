"""API routers package."""

from .common import router as common_router
from .config import router as config_router
from .main import router as main_router
from .papers import router as papers_router

__all__ = ["common_router", "config_router", "main_router", "papers_router"]
