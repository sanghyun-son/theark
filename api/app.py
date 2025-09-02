"""FastAPI application factory."""

import os
from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager

from fastapi import FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

from api.routers import (
    batch_router,
    common_router,
    config_router,
    crawler_router,
    main_router,
    papers_router,
)
from core import get_logger, setup_logging
from core.config import load_settings
from core.database.engine import create_database_tables
from core.services.summarization_service import PaperSummarizationService

logger = get_logger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
    """Application lifespan manager."""
    settings = load_settings()
    app.state.settings = settings
    setup_logging(
        level=settings.log_level,
        enable_file_logging=True,
    )
    logger.info(f"Starting TheArk API server in {settings.environment} mode")
    logger.info(f"Authentication required: {settings.auth_required}")

    from core.batch.background_manager import BackgroundBatchManager
    from core.database.engine import create_database_engine
    from core.extractors import extractor_factory
    from core.extractors.concrete import ArxivExtractor
    from core.llm.openai_client import UnifiedOpenAIClient

    # Create tables on startup
    engine = create_database_engine(settings.environment)
    create_database_tables(engine)
    app.state.engine = engine

    # Setup extractors
    extractor_factory.register_extractor("arxiv", ArxivExtractor())

    # Setup ArXiv source explorer
    from core.extractors.concrete.arxiv_source_explorer import ArxivSourceExplorer

    arxiv_explorer = ArxivSourceExplorer(
        api_base_url=settings.arxiv_api_base_url,
        delay_seconds=settings.arxiv_delay_seconds,
        max_results_per_request=settings.arxiv_max_results_per_request,
    )
    app.state.arxiv_explorer = arxiv_explorer

    # Setup historical crawl manager (if enabled)
    if settings.historical_crawl_enabled:
        from core.extractors.concrete.historical_crawl_manager import (
            HistoricalCrawlManager,
        )

        historical_crawl_manager = HistoricalCrawlManager(
            categories=settings.historical_crawl_categories,
            rate_limit_delay=settings.historical_crawl_rate_limit_delay,
            batch_size=settings.historical_crawl_batch_size,
        )
        app.state.historical_crawl_manager = historical_crawl_manager

        # Start the historical crawl manager with the explorer and engine
        try:
            await historical_crawl_manager.start(arxiv_explorer, engine)
            logger.info("Historical crawl manager started")
        except Exception as e:
            logger.error(f"Failed to start historical crawl manager: {e}")
    else:
        logger.info("Historical crawl manager disabled")

    # Setup CrawlService for API endpoints
    from core.services.crawl_service import CrawlService

    crawl_service = CrawlService(historical_crawl_manager)
    app.state.crawl_service = crawl_service

    fake_key = "*"
    openai_api_key = os.getenv("OPENAI_API_KEY", fake_key)
    if openai_api_key == fake_key:
        logger.warning("OPENAI_API_KEY is not set.")

    # Create OpenAI client
    openai_client = UnifiedOpenAIClient(
        api_key=openai_api_key,
        base_url=settings.llm_api_base_url,
        model=settings.llm_model,
        max_retries=settings.max_retries,
    )
    app.state.summary_client = openai_client

    app.state.background_batch_manager = BackgroundBatchManager(
        PaperSummarizationService(
            version=settings.version,
            default_interests=settings.default_interests_list,
        ),
        batch_enabled=settings.batch_enabled,
        batch_summary_interval=settings.batch_summary_interval,
        batch_fetch_interval=settings.batch_fetch_interval,
        batch_max_items=settings.batch_max_items,
        language=settings.default_summary_language,
        interests=settings.default_interests_list,
    )

    try:
        await app.state.background_batch_manager.start(
            engine,
            app.state.summary_client,
        )
    except Exception as e:
        logger.error(f"Failed to start background batch manager: {e}")

    logger.info("TheArk API server initialized successfully")

    yield

    # Stop background batch processing
    if hasattr(app.state, "background_batch_manager"):
        try:
            await app.state.background_batch_manager.stop()
        except Exception as e:
            logger.error(f"Error stopping background batch manager: {e}")

    # Stop historical crawl manager
    if hasattr(app.state, "historical_crawl_manager"):
        try:
            await app.state.historical_crawl_manager.stop()
        except Exception as e:
            logger.error(f"Error stopping historical crawl manager: {e}")

    logger.info("TheArk API server shutting down")


def create_app() -> FastAPI:
    """Create FastAPI app with current settings."""
    settings = load_settings()

    app = FastAPI(
        title=settings.api_title,
        description="Backend API for TheArk paper management system",
        version=settings.api_version,
        lifespan=lifespan,
    )

    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_allow_origins,
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
    app.include_router(crawler_router)
    return app


app = create_app()


@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception) -> None:
    """Global exception handler."""
    logger.error(f"Unhandled exception: {exc}", exc_info=True)
    raise HTTPException(status_code=500, detail=str(exc))
