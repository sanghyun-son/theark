"""FastAPI application factory."""

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
    statistics_router,
)
from api.services.app_initializer import AppServiceInitializer
from core import get_logger, setup_logging
from core.config import load_settings

logger = get_logger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
    """Application lifespan manager."""

    # 서비스 초기화
    settings = load_settings()
    app.state.settings = settings

    setup_logging(
        level=settings.log_level,
        enable_file_logging=True,
    )
    logger.info(f"Starting TheArk API server in {settings.environment} mode")
    logger.info(f"Authentication required: {settings.auth_required}")

    initializer = AppServiceInitializer(settings)
    await initializer.initialize_all_services(app)

    # Start all background services
    await initializer.start_all_services()

    logger.info("TheArk API server initialized and started successfully")
    yield

    await initializer.stop_all_services()
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
    app.include_router(statistics_router)
    return app


app = create_app()


@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception) -> None:
    """Global exception handler."""
    logger.error(f"Unhandled exception: {exc}", exc_info=True)
    raise HTTPException(status_code=500, detail=str(exc))
