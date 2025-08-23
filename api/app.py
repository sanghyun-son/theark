"""Main FastAPI application."""

from contextlib import asynccontextmanager
from typing import AsyncGenerator

from fastapi import FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

from core import get_logger
from core.config import load_settings

from .routers import common_router

logger = get_logger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
    """Application lifespan context manager."""
    current_settings = load_settings()
    logger.info(f"TheArk API server starting up in {current_settings.environment} mode")
    logger.info(f"Authentication required: {current_settings.auth_required}")
    yield
    logger.info("TheArk API server shutting down")


def create_app() -> FastAPI:
    """Create FastAPI app with current settings."""
    current_settings = load_settings()

    app = FastAPI(
        title=current_settings.api_title,
        description="Backend API for TheArk paper management system",
        version=current_settings.api_version,
        lifespan=lifespan,
    )

    # Add CORS middleware
    app.add_middleware(
        CORSMiddleware,
        allow_origins=current_settings.cors_allow_origins,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    app.mount("/static", StaticFiles(directory="static"), name="static")
    app.include_router(common_router)
    return app


app = create_app()


@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception) -> None:
    """Global exception handler."""
    logger.error(f"Unhandled exception: {exc}", exc_info=True)
    raise HTTPException(status_code=500, detail="Internal server error")
