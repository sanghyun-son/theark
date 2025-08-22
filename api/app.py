"""Main FastAPI application."""

from contextlib import asynccontextmanager
from typing import AsyncGenerator

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

from core import get_logger

from .routers import common_router

logger = get_logger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
    """Application lifespan context manager."""
    # Startup
    logger.info("TheArk API server starting up")
    yield
    # Shutdown
    logger.info("TheArk API server shutting down")


# Create FastAPI app
app = FastAPI(
    title="TheArk API",
    description="Backend API for TheArk paper management system",
    version="1.0.0",
    lifespan=lifespan,
)

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Configure appropriately for production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Mount static files
app.mount("/static", StaticFiles(directory="static"), name="static")

# Include routers
app.include_router(common_router)


@app.exception_handler(Exception)
async def global_exception_handler(request: object, exc: Exception) -> None:
    """Global exception handler."""
    logger.error(f"Unhandled exception: {exc}", exc_info=True)
    raise HTTPException(status_code=500, detail="Internal server error")
