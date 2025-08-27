"""Main FastAPI application."""

import logging
import os
from contextlib import asynccontextmanager
from typing import AsyncGenerator

from fastapi import FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

from core import get_logger, setup_logging
from core.config import load_settings

from .routers import (
    batch_router,
    common_router,
    config_router,
    main_router,
    papers_router,
)

settings = load_settings()
log_level = getattr(logging, settings.log_level.upper(), logging.INFO)
setup_logging(level=log_level, use_colors=True)

logger = get_logger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
    """Application lifespan context manager."""
    current_settings = load_settings()
    logger.info(f"TheArk: {current_settings.environment}")
    logger.info(f"Authentication required: {current_settings.auth_required}")

    from core.batch.background_manager import BackgroundBatchManager
    from core.database.config import get_database_path
    from core.database.implementations.sqlite import SQLiteManager
    from core.extractors import extractor_factory
    from core.extractors.concrete import ArxivExtractor
    from core.llm.openai_client import UnifiedOpenAIClient

    # Create tables on startup (without persistent connections)
    db_path = get_database_path(current_settings.environment)
    app.state.db_manager = SQLiteManager(db_path)
    await app.state.db_manager.connect()
    await app.state.db_manager.create_tables()

    # Setup extractors
    extractor_factory.register_extractor("arxiv", ArxivExtractor())

    fake_key = "*"
    openai_api_key = os.getenv("OPENAI_API_KEY", fake_key)
    if openai_api_key == fake_key:
        logger.warning("OPENAI_API_KEY is not set.")

    app.state.summary_client = UnifiedOpenAIClient(
        api_key=openai_api_key,
        base_url=current_settings.llm_api_base_url,
        model=current_settings.llm_model,
    )

    # Initialize background batch manager
    app.state.background_batch_manager = BackgroundBatchManager(current_settings)

    # Start background batch processing if enabled
    if current_settings.batch_enabled:
        try:
            await app.state.background_batch_manager.start(
                app.state.db_manager,
                app.state.summary_client,
            )
        except Exception as e:
            logger.error(f"Failed to start background batch manager: {e}")
    else:
        logger.info("Background batch processing is disabled")

    logger.info("TheArk API server initialized successfully")

    yield

    # Stop background batch processing
    if hasattr(app.state, "background_batch_manager"):
        try:
            await app.state.background_batch_manager.stop()
        except Exception as e:
            logger.error(f"Error stopping background batch manager: {e}")

    await app.state.db_manager.disconnect()
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

    app.add_middleware(
        CORSMiddleware,
        allow_origins=current_settings.cors_allow_origins,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    app.mount("/static", StaticFiles(directory="static"), name="static")
    app.include_router(main_router)
    app.include_router(common_router)
    app.include_router(config_router)
    app.include_router(papers_router)
    app.include_router(batch_router)
    return app


app = create_app()


@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception) -> None:
    """Global exception handler."""
    logger.error(f"Unhandled exception: {exc}", exc_info=True)
    raise HTTPException(status_code=500, detail=str(exc))
