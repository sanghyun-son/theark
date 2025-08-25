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

from .routers import common_router, config_router, main_router, papers_router

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

    from api.services.paper_service import PaperService
    from crawler.arxiv.client import ArxivClient
    from crawler.database import LLMSQLiteManager
    from crawler.database.config import get_database_path, get_llm_database_path
    from crawler.database.sqlite_manager import SQLiteManager
    from crawler.summarizer.openai_summarizer import OpenAISummarizer

    # Use current environment for database paths
    current_environment = current_settings.environment
    db_path = get_database_path(current_environment)
    db_manager = SQLiteManager(db_path)
    db_manager.connect()
    db_manager.create_tables()

    llm_db_path = get_llm_database_path(current_environment)
    llm_db_manager = LLMSQLiteManager(llm_db_path)
    llm_db_manager.connect()
    llm_db_manager.create_tables()

    arxiv_client = ArxivClient(base_url=current_settings.arxiv_url)

    fake_key = "*"
    openai_api_key = os.getenv("OPENAI_API_KEY", fake_key)
    if openai_api_key == fake_key:
        logger.warning("OPENAI_API_KEY is not set.")

    summary_client = OpenAISummarizer(
        api_key=openai_api_key,
        base_url=current_settings.llm_api_base_url,
    )

    app.state.db_manager = db_manager
    app.state.llm_db_manager = llm_db_manager
    app.state.paper_service = PaperService()
    app.state.arxiv_client = arxiv_client
    app.state.summary_client = summary_client
    logger.info("Database and LLM database initialized successfully")

    yield

    await app.state.paper_service.close()
    app.state.db_manager.disconnect()
    app.state.llm_db_manager.disconnect()
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
    return app


app = create_app()


@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception) -> None:
    """Global exception handler."""
    logger.error(f"Unhandled exception: {exc}", exc_info=True)
    raise HTTPException(status_code=500, detail=str(exc))
