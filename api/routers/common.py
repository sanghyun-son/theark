"""Common API endpoints router."""

import datetime
from pathlib import Path

from fastapi import APIRouter
from fastapi.responses import FileResponse, HTMLResponse
from pydantic import BaseModel

from core import get_logger

logger = get_logger(__name__)

router = APIRouter(tags=["common"])


class HealthResponse(BaseModel):
    """Health check response model."""

    status: str
    version: str
    timestamp: str


@router.get("/", response_class=HTMLResponse)
async def root() -> HTMLResponse:
    """Root endpoint with basic API information."""
    # Load HTML template
    template_path = Path("templates", "root.html")
    with open(template_path, "r", encoding="utf-8") as f:
        html_content = f.read()

    return HTMLResponse(content=html_content)


@router.get("/health", response_model=HealthResponse)
async def health_check() -> HealthResponse:
    """Health check endpoint."""
    return HealthResponse(
        status="healthy",
        version="1.0.0",
        timestamp=datetime.datetime.now().isoformat(),
    )


@router.get("/favicon.ico", response_model=None)
async def favicon() -> HTMLResponse:
    """Favicon endpoint - returns the favicon.ico file."""
    # Get the favicon path
    favicon_path = Path("static/favicon.ico")

    if favicon_path.exists():
        return FileResponse(favicon_path, media_type="image/x-icon")
    else:
        # Return a simple placeholder if favicon doesn't exist
        placeholder_content = "<!-- Placeholder favicon -->"
        return HTMLResponse(
            content=placeholder_content,
            status_code=200,
            headers={"Content-Type": "text/html"},
        )
